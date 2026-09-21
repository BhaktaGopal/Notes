**Redis Architecture And Distributed Caching:-**



**Why we can't just use one Redis?**



* Depends on the scale of the work.
* Problem 1- Capacity:

  * If multiple machines are there then due to limited memory one Redis instance has limited memory
* Problem 2- Availability:

  * We need distributed caching as if the application crashes we can't access the cache.
* SOLUTION:

  * Redis Replication:-

    * &#x20;Redis Primary --------- Repilca 1 \& Replica 2
    * The primary handles writes, while the replica maintains the copies of the data
    * If the primary dies then replica will be the new primary, called as **failover.**
    * It can not solve the memory problem only improves availability.
  * Redis Sharding:-

    * Instead of putting all keys on one Redis server, we distribute keys across multiple redis nodes.
    * To know which redis server has the required key we need to go through **consistent hashing ( uses hash ring, where querying keys are searched in cyclic manner).**
    * **Consistent hashing**  minimizes the number of keys to move when nodes are added or removed.

&#x09;		 

&#x09;But Redis cluster doesnot use traditional consistent hashing. It explicitly uses a fixed 16,384 hash-slot model.

What redis does is it divides the keyspace into 16,384 slots

Each key gets assigned to exactly ine slot, each master node owns a subset of those slots.



&#x09;It uses :- HASH\_SLOT = CRC16(KEY) % 16384



**Redis Cluster partitions keys using 16,384 hash slots, with slots assigned to cluster nodes.**



**WHAT HAPPNES WHEN REDIS GOES DOWN?**

* When the cache goes down all the requests goes to the DB directly and can lead to **cache failure storm.**
* So production system may use:-

  * Redis replication/failover
  * Request throttling
  * Circuit breakers
  * Local fallback caches
  * Database protection mechanisms





