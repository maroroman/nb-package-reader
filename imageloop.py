#!/usr/bin/python3

import openshift as oc
from time import sleep
from datetime import datetime
import requests
import os
import git
import yaml
import json

manifests = git.Repo.clone_from('https://github.com/red-hat-data-services/odh-manifests.git', 'manifests', branch='master')
nb_images = manifests.heads.master.commit.tree['jupyterhub']['notebook-images']['overlays']
additional = nb_images['additional']
cuda = nb_images['cuda']
cuda11_0_3 = nb_images['cuda-11.0.3']

for blob in additional.blobs:
    print(blob.name)


pod_template =  yaml.load('''
apiVersion: v1
kind: Pod
metadata:
  name: image
spec:
  containers:
    - name: image
      image: ''
      imagePullPolicy: Always
      command: ["/bin/bash"]
      args: ["-c", "more /etc/passwd; whoami; while true; do echo hello; sleep 5; done"]
''')



images = [
    {
    'name': 's2i-minimal',
    'image': 'quay.io/thoth-station/s2i-minimal-notebook:v0.0.15',
    'dependencies': [{"name":"JupyterLab","version": "3.0.14"}, {"name":
          "Notebook","version": "6.3.0"}],
    'software': [{"name":"Python","version":"v3.6.8"}]
    },
    {
    'name': 's2i-generic-data-science',
    'image': 'quay.io/thoth-station/s2i-generic-data-science-notebook:v0.0.5',
    'dependencies': [{"name":"Boto3","version":"1.17.11"},{"name":"Kafka-Python","version":"2.0.2"},{"name":"Matplotlib","version":"3.4.2"},{"name":"Numpy","version":"1.21.0"},{"name":"Pandas","version":"1.2.5"},{"name":"Scipy","version":"1.7.0"}],
    'software': [{"name":"Python","version":"v3.8.6"}]
    }
]
for image in images:
    pod = pod_template
    pod['metadata']['name'] = image['name']
    pod['spec']['containers'][0]['name'] = image['name']
    pod['spec']['containers'][0]['image'] = image['image']

    oc.apply(pod)

sleep(5)

def oc_exec(select, commands):
    return oc.selector('pod/%s' % select).object().execute(commands, container_name='%s' % select)

for image in images:

    freeze = oc_exec(image['name'], ['pip','list','--format','json'])
    python = oc_exec(image['name'], ['python','--version']).out().split()
    rpm_names = oc_exec(image['name'], ['rpm','-qa','--queryformat','%{NAME}\\n']).out().split('\n')
    rpm_versions = oc_exec(image['name'], ['rpm','-qa','--queryformat','%{VERSION}\\n']).out().split('\n')
    packages = json.loads(freeze.out())
    packages.append({'name': python[0], 'version': python[1]})
    rpm_list = []
    for index in range(len(rpm_names)-1):
        rpm_list.append({'name': rpm_names[index], 'version': rpm_versions[index]})

with open("output/RHDS-Notebook-packages-%s.md" % datetime.now().strftime("%d-%m-%Y-%H-%M-%S"), "w") as f:
    f.write('# PIP \n')
    for image in images:
        f.write('## ' + image['name'].upper() + '\n')
        for dependency in image['dependencies']:
            for package in packages:
                if dependency['name'].lower() == package['name'].lower():
                    f.write(str(package) + '\n')
                    if dependency['version'] != package['version']:
                        f.write('**WARN: Package version does not match! Given:%s Actual:%s' % (dependency['version'], package['version']) + '**\n')
        for software in image['software']:
            for package in packages:
                if software['name'].lower() == package['name'].lower():
                    f.write(str(package) + '\n')
                    if software['version'] != package['version']:
                        f.write('**WARN: Package version does not match! Given:%s Actual:%s' % (software['version'], package['version']) + '**\n')
        f.write('\n')

os.rmdir('manifests')
# both of these horrible horrible loops should use query instead of the large package list
# print('PIP \n')
# for image in images:
#     print(image['name'].upper() + '\n')
#     for dependency in image['dependencies']:
#         for package in packages:
#             if dependency['name'].lower() == package['name'].lower():
#                 print(package)
#     for software in image['software']:
#         for package in packages:
#             if software['name'].lower() == package['name'].lower():
#                 print(package)
#     print('\n')

# rpm doesn't seem to output anything useful

# print('RPM \n')
# for image in images:
#     print(image['name'].upper() + '\n')
#     for dependency in image['dependencies']:
#         for package in packages:
#             if dependency['name'].lower() == package['name'].lower():
#                 print(package)
#         for software in image['software']:
#             for package in packages:
#                 if software['name'].lower() == package['name'].lower():
#                     print(package)
#     print('\n')