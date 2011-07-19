__author__ = 'adam'

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


ssh.connect('epsilon', username='root', password='Qm146206')
stdin, stdout, stderr = ssh.exec_command('ls -alh')
print stdout.readlines()
ssh.close()