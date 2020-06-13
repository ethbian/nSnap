# nSnap
nmap Snapshotter:  
periodically scans your servers with nmap, shows the results and differences on a webpage:  
  
[nsnap-web: hosts](https://ethbian.org/images/nsnap/hosts.png)  
[nsnap-web: services](https://ethbian.org/images/nsnap/services.png)  
[nsnap-web: diffs](https://ethbian.org/images/nsnap/diffs.png)  

## quick start

### installation

#### a) clone the repository

> cd /tmp  
> git clone https://github.com/ethbian/nSnap.git  
> cd nSnap  
> chmod +x nsnap.py nsnap-web.py  

#### b) copy the files

> cp nsnap.py /usr/local/bin  
> mkdir -p /usr/local/share/nsnap  
> cp -r nsnap-web.py templates /usr/local/share/nsnap/  
> cp nsnap-web.service /lib/systemd/system/

#### c) install python dependencies

> pip3 install -r requirements.txt


### configuration

#### a) run as...

nmap requires root privileges to perform some types of scan, for example TCP SYN Stealth (-sS),  
so the easiest way of running nsnap is to run it as root. However, if you are ok with basic  
nmap scan - nsnap can run as any user (I'm skipping playing with sudo).  

#### b) nsnap.py

nsnap.py performs the scan and it's executed from crontab. Open the file with text editor
and check the variables:  
- install nmap and ndiff binaries, check NMAP_PATH and NDIFF_PATH (eg. apt-get install nmap ndiff)  
- create DBDIR directory (eg. mkdir /var/lib/nsnap). Change its owner if not running as root. 
- create NMAP_DIR directory (nmap scan reslut files). Change its owner if not running as root.  
- create LOG_FILE file (eg. touch /var/log/nsnap.log). Change its owner if not running as root.  
- change NMAP_TARGET - [nmap target selection](https://hackertarget.com/nmap-cheatsheet-a-quick-reference-guide)  
- change NMAP_OPTS ['as', 'a', 'python', 'list']

Execute the script from command line, see if it's working.  
Check the LOG_FILE for possible errors.  
If it's ok you can schedule the cron job, eg. once a day at 1:AM:
> 0 1 * * * /usr/local/bin/nsnap.py  

#### c) nsnap-web.py

You can run the script/service as any user.  
Open the file with text editor and check the variables:  
- DBPATH should point to the nmap.py's sqlite file (DBDIR/DBFILE)  
- HOST defines IP address the script will be running on  
- PORT defines its port number  

Just start the script:  
> /usr/local/share/nsnap/nsnap-web.py  

Open up your web browser and point it to http://HOST:PORT.  
Your first scan results should be already there. Every time nsnap.py is executed  
the scan results will be there. If something changes the difference will be shown  
in the Diff section.  

If you want to run nsnap-web as a service, in the background, just run the following:  
**systemctl start nsnap-web**  
**systemctl enable nsnap-web**  

Pull requests are more than welcome if you're fixing something.  