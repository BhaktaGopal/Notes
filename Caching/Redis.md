**Redis Architecture And Distributed Caching:-**



**Why we can't just use one Redis?**



* Depends on the scale of the work.
* **Problem** 1- **Capacity**:

  * If multiple machines are there then due to limited memory one Redis instance has limited memory
* **Problem** 2- **Availability**:

  * We need distributed caching as if the application crashes we can't access the cache.
* **SOLUTION**:

  * *Redis Replication*:-

    * &#x20;Redis Primary --------- Repilca 1 \& Replica 2
    * The primary handles writes, while the replica maintains the copies of the data
    * If the primary dies then replica will be the new primary, called as **failover.**
    * It can not solve the memory problem only improves availability.
  * *Redis Sharding*:-

    * Instead of putting all keys on one Redis server, we distribute keys across multiple redis nodes.
    * To know which redis server has the required key we need to go through **consistent hashing ( uses hash ring, where querying keys are searched in cyclic manner).**
    * **Consistent hashing**  minimizes the number of keys to move when nodes are added or removed.

      * While using consistent hashing, the key-to-node mapping changes for only a subset of keys.

&#x09;

&#x09;But Redis cluster does not use traditional consistent hashing. It explicitly uses a fixed 16,384 hash-slot model.

What redis does is it divides the keyspace into 16,384 slots

Each key gets assigned to exactly one slot, each master node owns a subset of those slots.



&#x09;It uses :- HASH\_SLOT = CRC16(KEY) % 16384



**Redis Cluster partitions keys using 16,384 hash slots, with slots assigned to cluster nodes.**



* SHARDING - distributes data/ increases capacity
* Replication- creates copies/improves availability



**WHAT HAPPNES WHEN REDIS GOES DOWN?**

* When the cache goes down all the requests goes to the DB directly and can lead to **cache failure storm.**
* So production system may use:-

  * Redis replication/failover
  * Request throttling
  * Circuit breakers
  * Local fallback caches
  * Database protection mechanisms





* FIRST PRINCIPLE:- Cache should usually fail open

  * We should try to continue serving from the database rather than making the entire application unavailable- **failing open.**

    * &#x20;		Redis

&#x20;  			  |

&#x09;		/   \\

&#x09;	       /     \\

&#x09;	      HIT    ERROR

&#x09;	      |       |

&#x09;	    Response  Database

* We can use small timeouts so that one failed cache won't block our application for a long time.(And we can also make sure retries to be limited)
* **Circuit Breaker-**

  * The circuit breaker observes failures and eventually prevents the application from continuously hammering a failed Redis cluster.
  * STAGES:-

    * CLOSED :- Everything is normal.

      * Request-> Redis
    * OPEN :- Too many failures occurred

      * Request-> Database(Redis is temporarily bypassed)
    * HALF-OPEN :- After some recovery period, allow a small number of test requests.

&#x20;



&#x20;     		CLOSED

&#x09;	  |

&#x09;	  |

&#x09;    TOO MANY FAILURES

&#x09;	  |

&#x09;	OPEN

&#x09;	  |

&#x09;	WAIT

&#x09;	  |

&#x09;      HALF OPEN

&#x09;	  |

&#x09;	 TEST

&#x09;	  |------SUCCESS--->CLOSED

&#x09;	  |------FAILURE--->OPEN



* LOCAL CACHE :- We can have small in-process cache in each application server.(Very frequently accessed data, short TTLs, relatively stable data, to be used)
* GRACEFUL DEGRADATION:- If the redis and db are under heavy load  we can provide a degraded response rather than failing every request.
* **COLD CACHE PROBLEM:-**

  * When the Redis comes back after been down for nearly 10 mins mostly it's empty and if n number of requests comes suddenly all the load will go on db.
  * So we can use **cache warming**  before exposing the recovered cache to the env we can reload it with frequently accessed data from db.
* Request coalescing :-

  * If the request asks for the same product continuously we can make the req hit the db once and that to be stored in the cache so that it won't be hitting the db again.
  * Don't make the backend perform the same expensive work repeatedly for concurrent identical requests.
* DB PROTECTION:-

  * If the redis fails we don't want unlimited traffic reacing the db so we an add Rate limiter-> concurrency limit-> database ( lets us control how much fallback traddic the db receives)



&#x09;







&#x09;		User

&#x09;		 |

&#x09;	    Load Balancer

&#x09;		 |

&#x09; +---------------+------------------+

&#x09; | 		 | 		    |

&#x09;App1		App2		   App3

&#x09; |		 |		    |

&#x09; +---------------+------------------+

&#x09;		 |

&#x09;	      Local Cache

&#x09;		 |

&#x09;	       Redis

&#x09;	      /	    \\

&#x09;	   Primary  Replica

&#x09;	     |

&#x09;	     DB



All around redis access:-

Application

&#x20;   |

Circuit Breaker

&#x20;   |

Redis

&#x20;   |

&#x20;   +---- success → return

&#x20;   |

&#x20;   +---- failure → fallback

&#x20;                      |

&#x20;                 Local Cache /

&#x20;                 Database /

&#x20;                 degraded response



**"If Redis fails, we need to fail fast on cache access and prevent all cache traffic from falling through to the database, otherwise the database can become overloaded and trigger a cascading failure."**

