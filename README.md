# docker-traefik-consul

Docker traefik backend does not currently support circuit-breakers.
This quick-and-dirty script that polls Docker for conteners with traefik labels, and populate a Consul key-value store.
With it, you have a fully automated traefik configuration WITH circuit breakers.


* Currently, Swarm parameters (TLS, IP, Port,...) are hard-coded into the script. (Facepalm). This has to be changed.
* Currentlty, the script polls Docker every 10s.

TODO : 
* Get rid of hard-coded docker & consul params.
* Make the frequency (10s) a parameter.
* Later, it will be interesting to use docker events instead of polling. It would less intrusive and more dynamic.
