# Caching — System Design Notes

## 1. What is Caching?

A **cache** is a temporary storage layer that keeps frequently accessed data closer to the application so that future requests can be served faster.

### Basic Flow

```text
User -> Application -> Cache
                       |
                       |-- HIT --> Response
                       |
                       |-- MISS
                              |
                           DATABASE
                              |
                         Update Cache
                              |
                           Response
```

It provides faster access to the data that we expect to need again.

---

## 2. Why Do We Need Caching?

If my application has **n requests/sec**, and most requests are for the same product, then without caching the database may be queried `n` times. This can be costly if `n` is too large.

With caching, if most requests are related to the same product, the database may only need to handle approximately:

```text
n - x
```

where `x` is the number of requests served from the cache.

### 3 Major Benefits

- **Lower latency** — Memory access is significantly faster than a database/network round trip.
- **Reduced database load** — The database does not need to repeatedly retrieve the same data.
- **Higher throughput** — Because many requests can be served directly from the cache, the system can handle more traffic.

---

# 3. Where Does the Cache Live?

There are two major categories:

1. **Local Cache**
2. **Distributed Cache**

---

## 3.1 Local Cache

A local cache lives in the RAM of the application server.

```text
        +----------------------+
User -->|     Application      |
        |                      |
        |     Local Cache      |
        +----------------------+
                   |
                   |
                Database
```

### Examples

- Python `Dictionary`
- Java `HashMap`
- Caffeine
- Guava Cache

### Advantages

- Very fast because there is no network call.
- Simple to implement.

### Disadvantages

#### Cache Inconsistency

When each server has a different cache, it can lead to cache inconsistency.

Initially:

```text
Server A -> name: Alice
Server B -> name: Alice
Database -> name: Alice
```

Someone changes the database:

```text
Database -> name: Jesh
```

Now:

```text
Server A -> name: Alice
Server B -> name: Alice
Database -> name: Jesh
```

So until the cache expires or is explicitly invalidated, the application could temporarily return **stale data**.

#### Memory Is Limited

If the cache grows too much, you can run into:

1. High memory usage
2. Garbage collection pressure
3. Process instability
4. Out-of-memory crashes

Therefore, eviction/expiration mechanisms are used, such as:

- LRU
- LFU
- TTL
- FIFO

#### Cache Disappears When the Application Restarts

Because the cache lives inside the application process, restarting the application normally removes the cached data.

#### Multiple Caches Need to Be Updated or Invalidated

If there is a change in the database, the corresponding entries in the other local caches may also need to be changed or invalidated.

---

## 3.2 Distributed Cache

A **distributed cache** is a cache that runs as a separate service/system, outside the application servers, and can be accessed by multiple application instances over the network.

### Examples

- Redis
- Memcached

Here, "distributed" means that the caching system provides cache functionality across a distributed application environment.

### Typical Architecture

```text
                    Load Balancer
                  /       |       \
                 /        |        \
              App1       App2      App3
                \          |         /
                 \         |        /
                  \        |       /
                       Redis
                         |
                      Database

Redis:
    user:123    -> Alice
    user:456    -> Bob
    product:10  -> iPhone
```

Even Redis itself can also be deployed as a distributed system.

### Advantages

- **Shared cache across servers**
- **Better support for horizontal scaling**
- **Better cache consistency** — your application still needs a sound invalidation/update strategy.
- **Reduced duplication**
- **Independent scaling**
- The cache can continue serving data when an application instance crashes/restarts.

### Disadvantages

- **Network latency**
- **Additional infrastructure**

---

# 4. Cache Terminology

## Cache Hit

If the data exists in the cache, it is a **cache hit**.

```text
Application -> Cache -> HIT -> Response
```

## Cache Miss

If the data does not exist in the cache, it is a **cache miss**.

```text
Application -> Cache -> MISS -> Database
```

## Cache Hit Ratio

```text
Cache Hit Ratio = Cache Hits / Total Requests
```

## Cache Miss Ratio

```text
Cache Miss Ratio = Cache Misses / Total Requests
```

## Stale Cache Data

When the data is updated in the database but the data in the cache is still not updated, the application may return **stale data**.

```text
Database -> New Value
Cache    -> Old Value
```

---

# 5. Cache-Aside

**Cache-aside** is also known as **lazy loading**.

The application itself manages the cache.

It is called lazy loading because we do not populate the cache ahead of time. The data enters the cache only when someone requests it.

---

## 5.1 TTL — Time To Live

When putting something into the cache, we can give it an expiration time.

Example:

```text
user:101 -> Alice
TTL = 300 seconds
```

---

## 5.2 Explicit Cache Invalidation

The application can explicitly invalidate cache data.

### Delete the Redis Key

Deleting the Redis key can result in a cache miss on the next read.

```text
Delete Cache Key
       |
       v
Next Read -> Cache Miss -> Database -> Cache
```

### Update the Redis Key

The application can also update the Redis key.

However, if the database update succeeds but the cache update does not, the cache can still contain stale data.

This is why cache consistency and invalidation strategy need to be considered carefully.

---

# 6. Four Important Cache Patterns

## 6.1 Cache-Aside — Read-Heavy Systems

The application directly controls both the database and cache.

### Read

```text
Application
     |
   Cache
   /   \
 HIT   MISS
  |      |
Return   DB
          |
          v
        Cache
          |
          v
       Response
```

### Write

A common cache-aside write flow is:

```text
WRITE / UPDATE
      |
      v
Application
      |
      v
Update Database
      |
      v
DB update succeeds
      |
      v
Delete Cache Entry
      |
      v
    Done
```

Later, during a read:

```text
Later: READ
      |
      v
    Cache
      |
     MISS
      |
      v
  Database
      |
      v
Put data in Cache
      |
      v
  Response
```

---

## 6.2 Write-Through

Here, the application writes to the cache, and the cache writes to the database.

```text
Application
     |
     v
   Cache
     |
     v
 Database
```

---

## 6.3 Write-Back / Write-Behind

Here, we write to the cache first.

```text
Application
     |
     v
   Cache
     |
     v
Response Immediately
```

Then later:

```text
Cache
  |
  v
Database
```

### Major Drawback

Data can be lost when the cache fails before the data reaches the database.

So this strategy is useful only in workloads where delayed persistence is acceptable and appropriate durability/recovery mechanisms are available.

---

## 6.4 Write-Around

The application writes directly to the database.

```text
Application
     |
     v
 Database
```

The cache is not updated during the write.

Later, when the data is read, it gets populated into the cache:

```text
Application
     |
     v
   Cache
     |
    MISS
     |
     v
  Database
     |
     v
   Cache
```

In practice, **write-around is often combined with cache invalidation**.

---

# 7. Cache Stampede / Thundering Herd

Suppose 10,000 users request the same product:

```text
product:p1001
```

They initially get the data from the cache.

Now the cache key expires.

If all 10,000 requests arrive around the same time:

```text
10,000 Requests
       |
       v
     Cache
       |
      MISS
       |
       v
    Database
       |
       v
   DB Overload
```

This is called a **cache stampede** or **thundering herd**.

---

# 8. Preventing Cache Stampede

## 8.1 Locking

Allow only one request to fetch the missing data.

```text
Request 1 -> Cache Miss -> Acquire Lock -> DB
Request 2 -> Cache Miss -> Wait
Request 3 -> Cache Miss -> Wait
Request 4 -> Cache Miss -> Wait
...
```

Once Request 1 gets the data:

```text
Database
    |
    v
  Cache
    |
    v
Other requests are fulfilled from cache
```

This can reduce many simultaneous database requests to a single database fetch.

---

## 8.2 Randomized TTL / TTL Jitter

Suppose 1 million keys have a TTL of 10 minutes and could expire together.

To reduce synchronized expiration, add randomness:

```text
TTL = 10 minutes + random(0-60 seconds)
```

For example:

```text
Key A -> 10m 12s
Key B -> 10m 43s
Key C -> 10m 05s
Key D -> 10m 51s
```

This spreads expirations over time.

---

## 8.3 Refresh Before Expiration

For very popular data, you can refresh the cache proactively before it expires.

```text
Cache Entry
Data in cache
TTL = 60s
    |
    v
TTL approaches expiration
    |
    v
Background Refresh
    |
    v
Database
    |
    v
Fresh Data
    |
    v
Update Cache
    |
    v
TTL = 60s
```

The main idea is:

> No need to wait for a cache miss to refresh very popular data.

---

# 9. Hot Key

A **hot key** is a single key that is requested by a large number of users at the same time.

### Prevention / Mitigation

- Replicate the hot value across multiple cache nodes.
- Use local caching at application servers.
- Use request coalescing so identical concurrent requests share one fetch.

---

# 10. Cache Penetration

Suppose users repeatedly request data that does not exist.

Without protection:

```text
Request
   |
Cache Miss
   |
Database
   |
No Data
```

Repeated requests can therefore cause repeated database hits.

One approach is to cache a `NULL`/not-found value:

```text
product:999 -> NULL
```

Then subsequent requests can be handled from the cache instead of repeatedly querying the database.

---

# 11. Cache Eviction / Expiration

## LRU — Least Recently Used

Removes the item that has not been accessed for the longest time.

```text
Least recently used -> Evict
```

## LFU — Least Frequently Used

Checks how many times an item has been accessed and removes the item with the lowest frequency.

```text
Lowest frequency -> Evict
```

## FIFO — First In, First Out

The oldest inserted item is removed first.

```text
First inserted -> Evict first
```

## TTL — Time To Live

Provides an expiration time for a cache entry. Once its expiration time is crossed, the entry expires according to the cache's expiration behavior.

```text
Key -> Value + Expiration Time
```

> **Note:** LRU, LFU, and FIFO are eviction policies, while TTL is primarily an expiration mechanism.

---

# 12. What Should You Cache?

A good general candidate is:

```text
High Read Frequency
        +
Relatively Low Change Frequency
        =
Good Cache Candidate
```

---

# 13. Questions to Consider When Designing a Cache

1. **WHAT should I cache?**
2. **WHEN should I read from the cache?**
3. **WHEN should I update/invalidate it?**
4. **HOW LONG should it remain there?**
5. **WHAT happens when the cache fails?**

---

# 14. Quick Revision

| Concept | Meaning |
|---|---|
| Cache | Temporary storage for frequently accessed data |
| Cache Hit | Requested data exists in cache |
| Cache Miss | Requested data does not exist in cache |
| Hit Ratio | Cache hits / total requests |
| Miss Ratio | Cache misses / total requests |
| Stale Data | Cache contains an outdated value |
| Local Cache | Cache inside application server memory |
| Distributed Cache | Separate cache service shared by application instances |
| Cache-Aside | Application manages cache and database; data is loaded lazily |
| Write-Through | Application writes to cache, which writes to database |
| Write-Back | Application writes to cache first; persistence happens later |
| Write-Around | Application writes directly to database; cache is populated later |
| Cache Stampede | Many requests hit the database after a cache miss/expiration |
| Hot Key | One key receives unusually high traffic |
| Cache Penetration | Requests for nonexistent data repeatedly reach the database |
| LRU | Evict least recently used item |
| LFU | Evict least frequently used item |
| FIFO | Evict oldest inserted item |
| TTL | Expiration time for cached data |

---

# 15. Mental Model

```text
                         CACHING
                            |
             +--------------+--------------+
             |              |              |
           WHERE           HOW            WHEN
             |              |              |
       Local / Redis    Read / Write   TTL / Invalidation
                            |
                 +----------+----------+
                 |          |          |
              Aside      Through     Back
                 |
                 +----------------------+
                                        |
                                  Edge Cases
                                        |
                       +----------------+----------------+
                       |                |                |
                    Stampede          Hot Key       Penetration
```

## Core Principle

> **Cache frequently accessed data to reduce latency and database load, while explicitly designing for consistency, expiration, eviction, failure, and high-concurrency edge cases.**
