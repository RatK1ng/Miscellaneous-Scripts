crm status
read -p "Press enter to continue..."
drbd-overview
read -p "Press enter to continue..."
df -h
read -p "Press enter to continue..."
top -n 1 |head -n 22
read -p "Press enter to continue..."
ps -ef| grep lsnr
read -p "Press enter to continue..."
su -c 'lsnrctl status; read -p "Press space to continue..."; /opt/oracle/product/12.1.0/db_home/bin/sqlplus / as sysdba @tbs_summary; exit' - oracle
# WIP Script by Jonathan Humphris