#!/usr/bin/python

import docker
import requests
import time
import os
import re

# http://IP:Port/v1/kv/
consul=os.environ['CONSULT_ROOT']

if os.environ['DOCKER_TLS_VERIFY']=="1":
    tls_config = docker.tls.TLSConfig(
        client_cert=(os.environ['DOCKER_CERT_PATH']+'/cert.pem', os.environ['DOCKER_CERT_PATH']+'/key.pem'),
        verify=False
        )
    base_url=re.sub("^tcp","https",os.environ['DOCKER_HOST'])
else:
    if "DOCKER_HOST" in os.environ.keys():
        base_url=re.sub("^tcp","http",os.environ['DOCKER_HOST'])
    else:
        base_url=""


client = docker.Client(base_url=base_url, tls=tls_config)


previous=[]
while True:
    root="test/"+str(time.time())
    kv={}
    rules={}
    nb_server={}
    print "checking"


    for dock in client.containers(filters={"label":"traefik.backend"}):
        # traefik.enable=false: disable this container in traefik
        if "traefik.enable" in dock["Labels"].keys():
            if dock["Labels"]["traefik.enable"]=="false":
                continue


        # traefik.backend=foo: assign the container to foo backend
        backend=dock["Labels"]["traefik.backend"]
        if backend not in rules.keys():
            rules[backend]=[]
        if backend not in nb_server.keys():
            nb_server[backend]=0
        nb_server[backend]=nb_server[backend]+1
        frontend="frontend-"+dock["Labels"]["traefik.backend"]
        kv["frontends/"+frontend+"/backend"]=backend

        # traefik.backend.maxconn.amount=10: set a maximum number of connections to the backend. Must be used in conjunction with the below label to take effect.
        if "traefik.backend.maxconn.amount" in dock["Labels"].keys():
            kv["backends/"+backend+"/maxconn/amount"]=dock["Labels"]["traefik.backend.maxconn.amount"]

        # traefik.backend.maxconn.extractorfunc=client.ip: set the function to be used against the request to determine what to limit maximum connections to the backend by. Must be used in conjunction with the above label to take effect.
        if "traefik.backend.maxconn.extractorfunc" in dock["Labels"].keys():
            kv["backends/"+backend+"/maxconn/extractorfunc"]=dock["Labels"]["traefik.backend.maxconn.extractorfunc"]

        # traefik.backend.loadbalancer.method=drr: override the default wrr load balancer algorithm
        if "traefik.backend.loadbalancer.method" in dock["Labels"].keys():
            kv["backends/"+backend+"/loadbalancer/method"]=dock["Labels"]["traefik.backend.loadbalancer.method"]

        # traefik.backend.loadbalancer.sticky=true: enable backend sticky sessions
        if "traefik.backend.loadbalancer.sticky" in dock["Labels"].keys():
            kv["backends/"+backend+"/loadbalancer/sticky"]=dock["Labels"]["traefik.backend.loadbalancer.sticky"]

        # traefik.backend.circuitbreaker.expression=NetworkErrorRatio() > 0.5: create a circuit breaker to be used against the backend
        if "traefik.backend.circuitbreaker.expression" in dock["Labels"].keys():
            kv["backends/"+backend+"/circuitbreaker/expression"]=dock["Labels"]["traefik.backend.circuitbreaker.expression"]

        server="server"+str(nb_server[backend])

        # traefik.protocol=https: override the default http protocol

        if "traefik.protocol" in dock["Labels"].keys():
            proto=dock["Labels"]["traefik.protocol"]
        else:
            proto="http"

        # traefik.port=80: register this port. Useful when the container exposes multiples ports.
        if "traefik.port" in dock["Labels"].keys():
            port=dock["Labels"]["traefik.port"]
        else:
            if proto=="http":
                port=80
            else:
                port=443

        # traefik.docker.network: Set the do
        if "traefik.docker.network" in dock["Labels"].keys():
            IP=dock["NetworkSettings"]["Networks"]["traefik.docker.network"]["IPAddress"]
        else:
            IP=dock["NetworkSettings"]["Networks"][dock["NetworkSettings"]["Networks"].keys()[0]]["IPAddress"]

        url=proto+"://"+IP+":"+str(port)

        kv["backends/"+backend+"/servers/"+server+"/url"]=url
        # traefik.weight=10: assign this weight to the container
        if "traefik.weight" in dock["Labels"].keys():
            kv["backends/"+backend+"/servers/"+server+"/weight"]=dock["Labels"]["traefik.weight"]
        else:
            kv["backends/"+backend+"/servers/"+server+"/weight"]="1"

        # traefik.frontend.rule=Host:test.traefik.io: override the default frontend rule (Default: Host:{containerName}.{domain}).
        if "traefik.frontend.rule" in dock["Labels"].keys():
            rule=dock["Labels"]["traefik.frontend.rule"]
            if rule not in rules[backend]:
                rules[backend].append(rule)
                kv["frontends/"+frontend+"/routes/test_"+str(len(rules[backend]))+"/rule"]=dock["Labels"]["traefik.frontend.rule"]

        # traefik.frontend.passHostHeader=true: forward client Host header to the backend.
        if "traefik.frontend.passHostHeader" in dock["Labels"].keys():
            kv["frontends/"+frontend+"/passHostHeader"]=dock["Labels"]["traefik.frontend.passHostHeader"]

        # traefik.frontend.priority=10: override default frontend priority
        if "traefikfrontend.priority" in dock["Labels"].keys():
            kv["frontends/"+frontend+"/priority"]=dock["Labels"]["traefik.frontend.priority"]

        # traefik.frontend.entryPoints=http,https: assign this frontend to entry points http and https. Overrides defaultEntryPoints.
        if "traefikfrontend.entryPoints" in dock["Labels"].keys():
            kv["frontends/"+frontend+"/entryPoints"]=dock["Labels"]["traefik.frontend.entryPoints"]


    print "Currents : "+str(len(kv))+" vs Previous :"+str(len(previous))
    if previous!=kv:
        print "Oh, I've got work to do"
        for item in kv.keys():
            print item+" ==> "+kv[item]
            r = requests.put(consul+root+"/"+item, data=kv[item])

        r = requests.put(consul+"intern/alias", data=root)
    else:
        print "sleeping"
    previous=kv
    time.sleep(10)
