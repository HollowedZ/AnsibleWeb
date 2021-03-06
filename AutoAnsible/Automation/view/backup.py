from __future__ import absolute_import, unicode_literals

from django.shortcuts import render, redirect
from django.http import HttpResponse
from users.forms import UserRegisterForm
from django.contrib.auth.decorators import login_required
from ..models import mac_os, PostInventoryGroup, PostInventoryHost ,PostPlayBookForm, TaskForm, log, group, addinfodevice , ios_router, preconfdevice, arp, kamusport, ios_switch, ios_switch_form, devices, iosrouter
from ..forms import ivlanset, backupset, hostnamecisco, dhcpset, ospfset, ip_staticset, vlanint, vlan_cisco, ospf_cisco, ciscobackup, ciscorestore, hostnamehuawei, ospf_huawei, intervlan_huawei, backupall, hostnamemikrotik, ipaddmikrotik, ospf_mikrotik, mikrotikbackup, huaweirestore, mikrotikrestore, autoconfig , vlanset, host_all
from django.contrib import messages
#from djansible.models import PlayBooks
from itertools import chain
from dj_ansible.models import AnsibleNetworkHost, AnsibleNetworkGroup
from dj_ansible.ansible_kit import execute  
import json
from datetime import datetime
import time
import threading
from django.contrib.auth.models import User

@login_required
def backup_all(request):
    if request.method=='POST':
        backup = backupset(request.POST, request.user)
        if backup.is_valid():
            print(request.POST)
            data = request.POST
            akun = request.user
            messages.success(request, f'Starting Backup Configuration!')
            for backups in backup:    
                tujuan = backups.cleaned_data.get('hosts')  
                target = tujuan.name         
                grup = AnsibleNetworkGroup.objects.filter(name=target).values_list('ansible_network_os')
                os = grup[0][0]
                t1 = threading.Thread(target=backup_act, args=[target, akun, os])
                t1.start()
                logs = log(account=akun, targetss=target, action="Backup Configuration "+target, status="PENDING", time=datetime.now(), messages="No Error")
                logs.save()
            context = {
                'backup': backup
            }
            return render(request, 'ansibleweb/backup.html', context)
    else:
        backup = backupset()

    context = {
        'backup': backup
    }
    return render(request, 'ansibleweb/backup.html', context)

def backup_act(target, akun,os):
    print("Starting Backup configuration")
    time.sleep(10)
    if os == 'ce':
        my_play = dict(
            name="Backup Configuration Huawei",
            hosts=target,
            become='yes',
            become_method='enable',
            gather_facts='no',
            tasks=[
                dict(action=dict(module='ce_config', lines=['sysname {{ inventory_hostname }}'], backup='yes'), register='output'),
                dict(action=dict(module='copy', src="{{output.backup_path}}", dest="./backup/{{inventory_hostname}}.cfg"))
            ]
        )
        result = execute(my_play)
        kondisi = result.stats
        kond = kondisi['has_changed']
        print(kond)
        if kond == True:
            logs = log.objects.filter(account=akun, targetss=target, action="Backup Configuration "+target, status='PENDING').update(status='Success')
        else:
            fail = result.results
            err = fail['failed'][0]['tasks'][0]['result']['msg'][0]
            logs = log.objects.filter(account=akun, targetss=target, action="Backup Configuration "+target, status='PENDING').update(status='Failed', messages=err)
            print(f'{err}')
    elif os == 'ios':
        my_play = dict(
            name="nyihuy",
            hosts=target,
            become='yes',
            become_method='enable',
            gather_facts='no',
            vars=[
                dict(ansible_command_timeout=120)
            ],
            tasks=[
                dict(action=dict(module='ios_config', backup='yes'), register='output'),
                dict(action=dict(module='copy', src="{{output.backup_path}}", dest="./backup/{{inventory_hostname}}.config")),
                dict(action=dict(module='lineinfile', path="./backup/{{inventory_hostname}}.config", line="Building configuration...", state='absent')),
                dict(action=dict(module='lineinfile', path="./backup/{{inventory_hostname}}.config", regexp="Current configuration.*", state='absent'))
                ]
            )
        result = execute(my_play)
        kondisi = result.stats
        kond = kondisi['has_changed']
        print(kond)
        print(result.results)
        if kond == True:
            logs = log.objects.filter(account=akun, targetss=target, action="Backup Configuration "+target, status='PENDING').update(status='Success')
            print(logs)
        else:
            fail = result.results
            err = fail['failed'][0]['tasks'][0]['result']['msg']
            logs = log.objects.filter(account=akun, targetss=target, action="Backup Configuration "+target, status='PENDING').update(status='Failed', messages=err)
            print(f'{err}')
    elif os == 'routeros':
        my_play= dict(
            name="Backup Mikrotik",
            hosts=target,
            become='yes',
            become_method='enable',
            gather_facts='no',
            vars=[
                dict(ansible_command_timeout=50)
            ],
            tasks=[
                dict(file=dict(path='./backup/{{inventory_hostname}}.backup', state='absent'))
                ]
            )              
        my_play2= dict(
            name="Backup Mikrotik",
            hosts=target,
            become='yes',
            become_method='enable',
            gather_facts='no',
            vars=[
                dict(ansible_command_timeout=120)
            ],
            tasks=[
                dict(action=dict(module='routeros_command', commands='/system backup save name={{ inventory_hostname }} password={{ ansible_password }}')),
                dict(net_get=dict(src="./{{ inventory_hostname }}.backup", protocol='scp', dest='./backup/{{ inventory_hostname}}.backup'))
                ]
        )
        my_play3 = dict(
            name="Backup",
            hosts=target,
            become='yes',
            become_method='enable',
            gather_facts='no',
            vars=[
                dict(ansible_command_timeout=120)
            ],
            tasks=[
                dict(action=dict(module='routeros_command', commands='/export'), register='export'),
                dict(action=dict(module='copy', content="{{ export.stdout|join('\n') }}", dest="./backup/{{ inventory_hostname }}.rsc"))
                ]
            )
        result = execute(my_play)
        result2 = execute(my_play2)
        result3 = execute(my_play3)
        kondisi = result2.stats
        kond = kondisi['has_changed']
        print(kond)
        print(json.dumps(result.stats, indent=4))
        print(json.dumps(result2.stats, indent=4))
        print(json.dumps(result3.stats, indent=4))
        if kond == True:
            logs = log.objects.filter(account=akun, targetss=target, action="Backup Configuration "+target, status='PENDING').update(status='Success')
        else:
            fail = result2.results
            err = fail['failed'][0]['tasks'][0]['result']['msg']
            logs = log.objects.filter(account=akun, targetss=target, action="Backup Configuration "+target, status='PENDING').update(status='Failed', messages=err)
            print(f'{err}')




