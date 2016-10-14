#!/usr/bin/python

import docker
import json
import requests
import time
#import consul
consul="http://192.168.99.104:8500/v1/kv/"


tls_config = docker.tls.TLSConfig(
  client_cert=('/home/fpege/.docker/machine/machines/swarm-master/cert.pem', '/home/fpege/.docker/machine/machines/swarm-master/key.pem'),
   verify=False
)
#verify=False,,ca_cert='/home/fpege/.docker/machine/machines/swarm-master/ca.pem'
client = docker.Client(base_url='https://192.168.99.105:3376', tls=tls_config)
# for evt in client.events():
#     data=json.loads(evt)
#     print json.dumps(data, sort_keys=True,indent=4, separators=(',', ': '))
#     print data["node"]['Name']
#     print data["Action"]
#     if "traefik.backend" in data["Actor"]["Attributes"].keys():
#         print data["Actor"]["Attributes"]["traefik.backend"]

previous=[]
while True:
    root="test/"+str(time.time())
    kv={}
    rules={}
    nb_server={}
    print "checking"

    print "Oh, I've got work to do"
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


    print json.dumps(kv, sort_keys=True,indent=4, separators=(',', ': '))
    #c = consul.Consul(host='192.168.99.104')
    current=requests.get(consul+root+"?recurse")


    print "Currents : "+str(len(kv))+" vs Previous :"+str(len(previous))
    if previous!=kv:
        for item in kv.keys():
            print item+" ==> "+kv[item]
            r = requests.put(consul+root+"/"+item, data=kv[item])

            #    c.kv.put(item,kv[item])
        r = requests.put(consul+"intern/alias", data=root)
        #index, data= c.kv.get(root)
        #print data
        print current.text
    else:
        print "sleeping"
    previous=kv
    time.sleep(10)
