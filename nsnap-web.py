#!/usr/bin/env python3

#
# version 1.0
# https://github.com/ethbian/nsnap
#

import os
import sqlite3
import datetime
import html
from flask import Flask
from flask import request
from flask import render_template
from flask_bootstrap import Bootstrap

DBPATH = '/var/lib/nsnap/nsnap.sqlite3'
HOST = '0.0.0.0'
PORT = 5000


class DB:
    def __init__(self):
        self.clear_errors()
        try:
            self.dbconn = sqlite3.connect(DBPATH)
            self.dbcursor = self.dbconn.cursor()
        except Exception as ex:
            self.error = True
            self.error_msg = ex

    def clear_errors(self):
        self.error = False
        self.error_msg = ''

    def dbcommit(self):
        self.dbconn.commit()

    def dbclose(self):
        self.dbconn.close()

    def get_hosts(self, id=0):
        self.clear_errors()
        all_hosts = []
        sql = 'SELECT * FROM hosts'
        if id != 0:
            sql += ' WHERE id={}'.format(id)
        try:
            self.dbcursor.execute(sql)
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            all_hosts = self.dbcursor.fetchall()
        return all_hosts

    def get_fullscan_dates(self, id=0):
        self.clear_errors()
        scan_timestamps = []
        scan_dates = {}
        id = int(id)
        sql = 'SELECT DISTINCT updated FROM fullscan'
        if id != 0:
            sql += ' WHERE id={}'.format(id)
        sql += ' ORDER BY updated DESC'
        try:
            result = self.dbcursor.execute(sql)
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            scan_timestamps = result.fetchall()
            for timestamp in scan_timestamps:
                scan_dates[timestamp[0]] = datetime.datetime.fromtimestamp(timestamp[0])
        return scan_dates

    def get_diffscan_dates(self, id=0):
        self.clear_errors()
        scan_timestamps = []
        scan_dates = {}
        id = int(id)
        sql = 'SELECT DISTINCT updated FROM diffscan'
        if id != 0:
            sql += ' WHERE id={}'.format(id)
        sql += ' ORDER BY updated DESC'
        try:
            result = self.dbcursor.execute(sql)
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            scan_timestamps = result.fetchall()
            for timestamp in scan_timestamps:
                scan_dates[timestamp[0]] = datetime.datetime.fromtimestamp(timestamp[0])
        return scan_dates

    def get_services(self, id=0, updated=0):
        self.clear_errors()
        all_services = []
        id = int(id)
        updated = int(updated)
        sql = 'SELECT * FROM fullscan WHERE '
        if updated == 0:
            sql += 'updated=(SELECT DISTINCT updated FROM fullscan ORDER BY updated DESC LIMIT 1)'
        else:
            sql += 'updated={}'.format(updated)
        if id != 0:
            sql += ' AND id={}'.format(id)
        try:
            result = self.dbcursor.execute(sql)
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            all_services = result.fetchall()
        return(all_services)

    def get_diffs(self, updated=0):
        self.clear_errors()
        all_diffs = []
        updated = int(updated)
        sql = 'SELECT * FROM diffscan'
        if updated != 0:
            sql += ' WHERE updated={}'.format(updated)
        sql += ' ORDER BY updated DESC'
        try:
            result = self.dbcursor.execute(sql)
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            all_diffs = result.fetchall()
        return(all_diffs)

    def get_diff_history(self, id=0):
        self.clear_errors()
        all_diffs = []
        id = int(id)
        sql = 'SELECT * FROM diffscan WHERE id={} ORDER BY updated DESC'.format(id)
        try:
            result = self.dbcursor.execute(sql)
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            all_diffs = result.fetchall()
        return(all_diffs)

    def get_single_diff(self, id=0, updated=0):
        self.clear_errors()
        id = int(id)
        updated = int(updated)
        comment = []
        sql = 'SELECT * FROM diffscan WHERE id={} AND updated={}'.format(id, updated)
        try:
            result = self.dbcursor.execute(sql)
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            comment = result.fetchone()
        return comment

    def post_diff_comment(self, hostid=0, updated=0, comment=''):
        self.clear_errors()
        hostid = int(hostid)
        updated = int(updated)
        try:
            self.dbcursor.execute("UPDATE diffscan SET comment=? WHERE id=? AND updated=?", (comment, hostid, updated))
            self.dbcommit()
        except Exception as ex:
            self.error = True
            self.error_msg = ex
        else:
            if self.dbcursor.rowcount < 1:
                return False
        return True


app = Flask(__name__)
Bootstrap(app)


@app.route('/host')
def single_host():
    hostid = request.args.get('hostid', default=0, type=int)
    host = []
    db = DB()
    if not db.error:
        host = db.get_hosts(hostid)[0]
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    last_scan = []
    last_scan = db.get_services(hostid)
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    if len(last_scan) > 0:
        last_scan_date = str(datetime.datetime.fromtimestamp(last_scan[0][1]))
    else:
        last_scan_date = ''

    diff_history = db.get_diff_history(hostid)
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    db.dbclose()
    diff_history = [list(diff) for diff in diff_history]
    for idx, diff in enumerate(diff_history):
        diff_history[idx][2] = diff[2].replace('\n', '<br/>')
        diff_history[idx].append(datetime.datetime.fromtimestamp(diff_history[idx][1]))
    return render_template('hosts.j2', host=host, last_scan=last_scan,
                           diff_history=diff_history, last_scan_date=last_scan_date)


@app.route('/services')
@app.route('/services/<timestamp>')
def services(timestamp=0):
    all_hosts = []
    db = DB()
    timestamp = int(timestamp)
    if not db.error:
        all_hosts = db.get_hosts()
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    all_hosts_by_id = {}
    for host in all_hosts:
        all_hosts_by_id[host[0]] = host
    all_services = db.get_services(updated=timestamp)
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    scan_dates = db.get_fullscan_dates()
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    db.dbclose()
    scan_date = '0'
    if timestamp != 0:
        scan_date = str(datetime.datetime.fromtimestamp(timestamp))
    return render_template('services.j2', all_hosts=all_hosts_by_id,
                           all_services=all_services, scan_dates=scan_dates,
                           scan_date=scan_date)


@app.route('/diffs', methods=['GET', 'POST'])
@app.route('/diffs/<timestamp>')
def diffs(timestamp=0):
    updated_result = 0
    if request.method == 'POST':
        hostid = int(request.form.get('hostid'))
        timestamp = int(request.form.get('timestamp'))
        comment = request.form.get('comment')
        comment = html.escape(comment)
        db = DB()
        if not db.error:
            result = db.post_diff_comment(hostid, timestamp, comment)
        if db.error:
            return render_template('error.j2', error_msg=db.error_msg)
        if result:
            updated_result = 1
        else:
            updated_result = 2
        db.dbclose()
        timestamp = 0
    all_hosts = []
    db = DB()
    timestamp = int(timestamp)
    if not db.error:
        all_hosts = db.get_hosts()
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    all_hosts_by_id = {}
    for host in all_hosts:
        all_hosts_by_id[host[0]] = host
    all_diffs = db.get_diffs(updated=timestamp)
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    diff_dates = db.get_diffscan_dates()
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    db.dbclose()
    all_diffs = [list(diff) for diff in all_diffs]
    for idx, _ in enumerate(all_diffs):
        all_diffs[idx][2] = all_diffs[idx][2].replace('\n', '<br/>')
        all_diffs[idx].append(datetime.datetime.fromtimestamp(all_diffs[idx][1]))
    diff_date = '0'
    if timestamp != 0:
        diff_date = str(datetime.datetime.fromtimestamp(timestamp))
    return render_template('diffs.j2', all_hosts=all_hosts_by_id, all_diffs=all_diffs,
                           diff_dates=diff_dates, diff_date=diff_date, updated_result=updated_result)


@app.route('/comment/<hostid>/<timestamp>')
def do_comment(hostid=0, timestamp=0):
    hostid = int(hostid)
    timestamp = int(timestamp)
    db = DB()
    if not db.error:
        host = db.get_hosts(hostid)[0]
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    thediff = db.get_single_diff(hostid, timestamp)
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    db.dbclose()
    thediff = list(thediff)
    thediff[2] = thediff[2].replace('\n', '<br/>')
    thediff.append(datetime.datetime.fromtimestamp(thediff[1]))
    return render_template('comment.j2', host=host, thediff=thediff)


@app.route('/')
def overview():
    all_hosts = []
    db = DB()
    if not db.error:
        all_hosts = db.get_hosts()
    if db.error:
        return render_template('error.j2', error_msg=db.error_msg)
    db.dbclose()
    return render_template('overview.j2', all_hosts=all_hosts)


if __name__ == "__main__":
    if not os.path.exists(DBPATH):
        raise SystemExit('DB file does not exist')
    # just in case:
    # app.run(host=HOST, port=PORT, debug=True)
    from waitress import serve
    serve(app, host=HOST, port=PORT)
