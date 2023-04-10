# E2E test for AWX integration

This subproject allows to run a k8s cluster for testing using kind and install AWX in it.
Kind is a tool for running local k8s clusters using docker/podman containers as nodes.

# Create a k8s cluster with kind

Requirements:

* docker/podman
* ansible
* kind <https://kind.sigs.k8s.io/docs/user/quick-start/#installation>
* kubernetes ansible collection `ansible-galaxy collection install kubernetes.core`

You may need to install the requirements with `pip install -r requirements.txt`
if you are not using the ansible-rulebook dev environment.

# Steps

1. Create the cluster

```
ansible-playbook create-cluster.yml
```

2. Install AWX

```
ansible-playbook install-awx.yml
```

You should be able to reach awx in <https://localhost:9443> with admin/password

# Cleanup

```
kind delete cluster -n awx-kind-cluster
```
