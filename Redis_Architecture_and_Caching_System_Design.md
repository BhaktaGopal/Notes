# Redis Architecture and Distributed Caching

## Why Can't We Just Use One Redis?

It depends on the scale of the work.

### Problem 1 — Capacity

- If multiple machines are there, then due to limited memory, one Redis instance has limited memory.

### Problem 2 — Availability

- We need distributed caching because if the application crashes, we can't access the cache.

## Solution

### 1. Redis Replication

```text
Redis Primary
      |
      +------ Replica 1
      |
      +------ Replica 2
```

- The primary handles writes, while the replicas maintain copies of the data.
- If the primary dies, a replica can become the new primary. This is called **failover**.
- Replication cannot solve the memory problem; it mainly improves **availability**.

### 2. Redis Sharding

Instead of putting all keys on one Redis server, we distribute keys across multiple Redis nodes.

To know which Redis server has the required key, we need to go through **consistent hashing**:

```text
Key
 |
 v
Hash
 |
 v
Hash Ring
 |
 +----> Redis Node
```

- Consistent hashing minimizes the number of keys that need to move when nodes are added or removed.
- While using consistent hashing, the key-to-node mapping changes for only a subset of keys.

---

## Redis Cluster and Hash Slots

Redis Cluster does not use traditional consistent hashing. It explicitly uses a fixed **16,384 hash-slot model**.

What Redis does is divide the keyspace into **16,384 slots**.

- Each key gets assigned to exactly one slot.
- Each master node owns a subset of those slots.

The hash-slot calculation is:

```text
HASH_SLOT = CRC16(KEY) % 16384
```

> **Redis Cluster partitions keys using 16,384 hash slots, with slots assigned to cluster nodes.**

### Sharding vs Replication

| Concept | Purpose |
|---|---|
| **Sharding** | Distributes data / increases capacity |
| **Replication** | Creates copies / improves availability |

---

# What Happens When Redis Goes Down?

When the cache goes down, all the requests can go to the database directly and can lead to a **cache failure storm**.

So a production system may use:

- Redis replication / failover
- Request throttling
- Circuit breakers
- Local fallback caches
- Database protection mechanisms

---

## First Principle — Cache Should Usually Fail Open

We should try to continue serving from the database rather than making the entire application unavailable. This is **failing open**.

```text
          Redis
            |
       +----+----+
       |         |
      HIT      ERROR
       |         |
       v         v
   Response   Database
```

We can use **small timeouts** so that one failed cache does not block the application for a long time.

We can also make sure retries are limited.

---

# Circuit Breaker

The circuit breaker observes failures and eventually prevents the application from continuously hammering a failed Redis cluster.

## Circuit Breaker Stages

### CLOSED

Everything is normal.

```text
Request → Redis
```

### OPEN

Too many failures have occurred.

```text
Request → Database
```

Redis is temporarily bypassed.

### HALF-OPEN

After some recovery period, allow a small number of test requests.

```text
CLOSED
   |
   | Too many failures
   v
 OPEN
   |
   | Wait
   v
HALF-OPEN
   |
   | Test
   +------ Success ------> CLOSED
   |
   +------ Failure ------> OPEN
```

---

# Local Cache

We can have a small **in-process cache** in each application server.

It can be useful for:

- Very frequently accessed data
- Short TTLs
- Relatively stable data

A simplified structure is:

```text
Application
     |
Local Cache
     |
   Redis
     |
  Database
```

---

# Graceful Degradation

If Redis and the database are under heavy load, we can provide a **degraded response** rather than failing every request.

For example, non-critical information can be temporarily unavailable while the core response is still served.

---

# Cold Cache Problem

When Redis comes back after being down for nearly 10 minutes, it may be mostly empty.

If a large number of requests suddenly arrive, all the load can go to the database:

```text
Redis comes back
      |
      v
Mostly empty cache
      |
      v
Many requests
      |
      v
Many cache misses
      |
      v
Database gets overloaded
```

## Cache Warming

We can use **cache warming** before exposing the recovered cache to the environment.

The idea is to reload frequently accessed data from the database:

```text
Database
   |
   v
Frequently accessed data
   |
   v
Redis
```

---

# Request Coalescing

If multiple requests ask for the same product continuously, we can make the request hit the database once and store the result in the cache so that the database is not hit repeatedly.

```text
100 identical requests
          |
          v
   One database request
          |
          v
        Cache
          |
          v
   Share the result
```

> Don't make the backend perform the same expensive work repeatedly for concurrent identical requests.

---

# Database Protection

If Redis fails, we don't want unlimited traffic reaching the database.

We can use:

```text
Rate Limiter
      |
      v
Concurrency Limit
      |
      v
Database
```

This lets us control how much fallback traffic the database receives.

---

# Resilient Redis Architecture

```text
                         User
                           |
                           v
                    Load Balancer
                           |
             +-------------+-------------+
             |             |             |
            App1          App2          App3
             |             |             |
             +-------------+-------------+
                           |
                      Local Cache
                           |
                         Redis
                        /     \
                   Primary   Replica
                       |
                       v
                      DB
```

---

# Redis Access Flow with Failure Handling

```text
Application
     |
     v
Circuit Breaker
     |
     v
   Redis
     |
     +---- Success ----> Return
     |
     +---- Failure ----> Fallback
                              |
                    +---------+---------+
                    |         |         |
                    v         v         v
               Local Cache  Database  Degraded
                                      Response
```

---

# Key Takeaway

> **"If Redis fails, we need to fail fast on cache access and prevent all cache traffic from falling through to the database, otherwise the database can become overloaded and trigger a cascading failure."**
