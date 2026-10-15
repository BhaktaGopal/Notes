**LOAD BALANCER:-**



* Spreads incoming traffic so no single server is overwhelmed and stops sending anyone to a server that has died.
* **WHY DO WE NEED LOAD BALANCER?**
* **ANSWER**->

&#x09;E.g, Suppose one store is there, It has one server in beginning

&#x09;	User(1,2,3,4,5) - Server

&#x09;   This server's capacity can handle this much.

&#x09;   What is suddenly the number of users increased?(on Black Friday)How the server will manage?

&#x09;	User(1,2,3,4,5,6,7,8,9,10) - Server

&#x09;

&#x09;-  Vertical Scaling>

&#x09;

&#x09;		We can increase the CPU capability in accordance to the requests.

&#x09;		But there is still a possibility that the number of requests can top the threshold of the CPU limit.

&#x09;		Myth- A bigger server solves everything.

&#x09;		Real- A bigger server is still a single server.

&#x09;- Horizontal Scaling>

&#x09;

&#x09;		We can increase the number of servers in accordance to the number of requests we are getting.

&#x09;		User(1,2,3,4,5,6,7,8,9,10) - Servers(1,2,3)

&#x09;		But still what if one server dies and the requests still be going towards that server which can lead to Errors in mass. And one server 			still can get overloaded and other servers can be still with light load.



&#x09;So to manage workload gets divided ideally and make sure the requests handled by the server is alive We need **LOAD BALANCER.**

&#x09;		Hz Scaling - Pros>> no hard ceiling

&#x09;				     Survives a failure if any server fails

&#x09;			      Cons>> Needs load balancer 

&#x09;				     Shared state is difficult as requests can go to any server.



* **ALGORITHMS USED BY LOAD BALANCER**
* **---->**

  * **STATIC ALGORITHM:-** eg. it provides a fixed order for the requests to be processed.
  * **DYNAMIC ALGORITHM:-** eg. Checks which server is less busy and chooses it to process the request.
  * **ROUND ROBIN ALGORITHM:-**  	Request1- Server1

&#x09;			Request2- Server2

&#x09;			Request3- Server3

&#x09;			Request4- Server1

&#x09;			   .      Server2

&#x09;			   .      Server3

&#x09;			HAProxy calls it the smoothest and fairest choice when the processing time stays **"evenly distributed"**.



&#x09;			*What is the power of the servers is not equally strong?*

&#x09;- **WEIGHTED ROUND ROBIN ALGORITHM:-** More requests are transferred to the stronger servers while the ones with less computational power are provided 					   with less number of requests.

&#x09;			Servers- A(Strong),B(Strong),C(Weak)

&#x09;			Requests-  4      , 4       , 1

&#x09;

&#x09;			*But it ignores the time required for each requests to process. What if some requests take more time than the others how they 				can be assigned accordingly.*

&#x09;			*-We can make the balancer to keep the track of the works the server is still doing, so that the requests can go the server 				 with least active connections/requests*(Least Connections).\*\*

&#x09;

&#x09;			*What if the server shows 0?*

&#x09;		*-      Servers - (A,B,C)*

&#x09;		       \*'A' can show 0 without being ready at all.

&#x09;		       \*'C' comes back from an update at 0.

&#x09;		       \* A broken server also gives 0 and becomes top priority for attending the requests, unless health checks catches it.

&#x09;			-On AWS's Application LoadBalancer, slow  start ramps a new target up linearly over a window you set between 30-900 seconds.

&#x09;



&#x09;

* 

&#x20;



&#x09;

&#x09;

