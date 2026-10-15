# Object Storage Explained 

**Based on:** *Object Storage Explained: Full Guide to System Design* — [YouTube video](https://www.youtube.com/watch?v=anLX4upY0ks)  
**Purpose:** Beginner-friendly study notes for understanding object storage, Amazon S3 concepts, design trade-offs, and common system-design patterns.

> **Source note:** These notes explain the ideas and examples presented in the supplied transcript. Product limits, API behavior, prices, and retrieval timings quoted from the video can change, so verify current provider documentation before using them in a production design.

---

## 1. The Core Mental Model

### 1.1 What is object storage?

Object storage keeps a complete unit of data—called an **object**—under a unique **key**. The object consists mainly of:

- **Data / bytes:** the contents, such as an image, video, PDF, backup, or dataset.
- **Metadata:** descriptive information, such as content type, object length, and last-modified time.
- **Key:** the name used to address and retrieve the object.

A simple way to picture it is a very large lookup table:

```text
(bucket, key, version)  ->  object bytes + descriptive information
```

For example:

```text
Bucket: creator-media
Key:    uploads/2026/raw/clip-8f3a.mp4
Value:  the complete video object and its metadata
```

The key is the object's address. In the general-purpose object-storage model described in the video, you do not open the object and edit arbitrary bytes in place. You usually write a replacement object instead.

### 1.2 The two ideas that explain most of the design

Almost every later rule follows from these two characteristics:

1. **The key is the primary way to address an object.** The object store does not automatically behave like a relational database with arbitrary queries and secondary indexes.
2. **Objects are effectively immutable after they are written.** A logical update usually means writing a new object or version, not editing a few bytes in the old one.

These choices let object stores scale to very large collections of objects, but they also create important design constraints.

### 1.3 What object storage is good at

Object storage is a strong fit when data is written as a whole and then read many times, for example:

- Photos, videos, audio, and other media files.
- Backups and archives.
- Data-lake files and analytical datasets.
- Static files delivered to users around the world.
- Large output files produced by a processing pipeline.

It is a weaker fit when an application must frequently change a small part of a file, needs normal filesystem behavior, or needs database-style filtering over arbitrary object attributes without maintaining additional indexes.

**Important point:** Object storage is not simply “a folder in the cloud.” Think of it as an API-accessible collection of named objects.

---

## 2. Buckets, Objects, Keys, Metadata, Tags, and Prefixes

### 2.1 Bucket

A **bucket** is a named container or namespace into which objects are stored. In the video's S3 example, `creator-media` is the bucket.

The bucket name identifies the collection; the object key identifies a particular object inside it.

### 2.2 Object key

An **object key** is the full name used to access an object. Example:

```text
uploads/2026/raw/clip-8f3a.mp4
```

The key may look like a filesystem path, but the slashes do not automatically create real directories in a general-purpose bucket. For the object store, the key is a string.

### 2.3 Metadata: descriptive information written with the object

Metadata is a set of name-value pairs associated with an object. The transcript distinguishes between:

- **System/service metadata:** information such as content type, length, and last-modified time.
- **User-supplied metadata:** descriptive values chosen by the uploader.

The key limitation is that metadata is treated as part of the object's written description. In the model explained by the video, changing metadata requires copying the object and setting the new metadata on the copy.

**Why this matters:** Suppose a 4.2 GB video has the wrong content type. Correcting one metadata field may require a copy operation involving the full object rather than a tiny metadata-only edit.

### 2.4 Tags: mutable labels

**Tags** provide labels that can be changed after an object is uploaded. They are useful when the classification of an object changes over time.

Example:

```text
At upload:  processing-status = raw
Later:      processing-status = finished
```

The object's bytes do not need to change when the tag changes.

Tags are useful for:

- Categorizing objects along additional dimensions.
- Filtering objects for lifecycle rules.
- Supporting more targeted access-policy decisions.
- Tracking a changing processing state.

The transcript says that S3 supports up to ten tags per object and describes tag reads as strongly consistent. Treat service limits as details to verify in current documentation before implementation.

### 2.5 Metadata versus tags

| Feature | Metadata | Tags |
|---|---|---|
| Main purpose | Describe the object | Label/classify the object |
| When is it set? | Commonly when the object is written | At upload or later |
| Can it be changed directly later? | The transcript says no; copy the object to change it | Yes, tags can be updated separately |
| Example | `Content-Type: video/mp4` | `processing-status=finished` |
| Typical design implication | Decide carefully before upload | Use for labels that may change over time |

### 2.6 Prefixes are not real folders

A key such as:

```text
uploads/2026/raw/clip-8f3a.mp4
```

looks hierarchical, but in a general-purpose bucket the apparent folders are derived from **prefixes**—shared beginnings of keys. A console can display folder-like groupings by using a delimiter in a list request.

This means there may be no actual directory object for `uploads/2026/raw/`.

Consequences:

- There may be no folder object with its own size or metadata.
- “Renaming a folder” means changing the keys of objects under that prefix.
- Moving a large prefix may require copying/replacing many objects and deleting the old keys.
- A console's folder view is a convenient representation, not proof that the underlying namespace is a filesystem.

### 2.7 Why keys matter beyond naming

A key schema is not just a readability choice. As explained later, the beginning of the key can also affect how requests are distributed across partitions. So a key design should consider both:

- **Application organization:** Can people and services construct or recognize the key?
- **Request distribution:** Does the key pattern concentrate too much traffic on a narrow set of prefixes?

---

## 3. Object Updates, Renames, Search, and Concurrency

### 3.1 No ordinary in-place editing

In a general-purpose bucket, the video describes objects as sealed once written:

- No ordinary append operation.
- No editing a small region in place.
- No cheap rename operation.

To replace an object, write a new object. To rename it, the normal pattern is **copy to a new key, then delete the old key**.

For a 4.2 GB video, this is very different from changing a few bytes: the replacement/copy can involve reading and writing the full 4.2 GB object.

**Design lesson:** Prefer workflows that produce a complete new object rather than repeatedly making tiny changes to one large object.

### 3.2 Searching for objects

Object storage is not automatically a query engine. In the model described in the transcript, the basic tools for finding objects are:

- An exact key, if you know it.
- A key prefix.
- A delimiter used to group keys in a listing.
- Listing and pagination.

The video states that a list operation returns at most **1,000 keys per request**, so very large collections require many paginated requests. A general-purpose bucket does not automatically offer SQL-like filtering such as “find every video whose resolution is 4K” just because the information exists somewhere in your application.

For richer searches, real systems commonly keep a separate index in a database or query inventory files. The database stores searchable attributes and the key that points to the object.

Example of a separate index conceptually:

| asset_id | resolution | status | object_key |
|---|---|---|---|
| `clip-8f3a` | `4K` | `finished` | `uploads/2026/finished/clip-8f3a.mp4` |

The object store holds the large bytes; a separate index makes it easier to search by application attributes.

### 3.3 Atomicity for one key versus multiple keys

The transcript makes an important distinction:

- **A single object's update is atomic:** a reader sees the old object or the new object rather than a mixture of their bytes.
- **A group of updates across multiple keys is not one atomic transaction:** the object store does not automatically make several object changes appear as one all-or-nothing database transaction.

When multiple writers update the same key, the video says the latest-timestamp write wins. Applications that need stronger coordination should design for it explicitly rather than assume database-style transactions or locking across object keys.

### 3.4 Exception described in the video: S3 Express One Zone

The transcript distinguishes general-purpose buckets from **directory buckets** used by S3 Express One Zone. It says that this product supports append and a rename operation that can complete atomically without moving the object's data.

The stated trade-off is important: Express One Zone stores data in a **single Availability Zone**, unlike storage classes designed to span multiple zones. Therefore, do not generalize a feature of directory buckets to every S3 bucket type.

**Important point:** When someone says “S3 supports rename” or “S3 does not support rename,” ask which bucket type and API they mean.

---

## 4. Object Storage vs. Block Storage vs. File Storage

The video recommends choosing storage based on how applications access data—not merely on file size.

### 4.1 Block storage

Block storage presents a volume as numbered blocks or offsets, similar to a disk. The operating system or application builds higher-level structures such as a filesystem on top of it.

The transcript uses Amazon EBS as the example.

**Typical characteristics:**

- Good for frequent small reads and writes at known offsets.
- Supports in-place modifications of blocks.
- Commonly attached to one host at a time in the described setup.
- Does not, by itself, provide coordination when multiple machines write to the same blocks.

**Example use case:** A PostgreSQL data volume, which continuously updates small pages at known positions and needs low-latency access.

### 4.2 File storage

File storage exposes files and directories through a filesystem protocol. It can provide familiar semantics such as permissions, locking, and coordinated access from multiple machines.

The transcript uses Amazon EFS and NFS as examples.

**Typical characteristics:**

- Many machines can mount and access the same filesystem.
- File and directory semantics are available.
- Locking and permission rules can coordinate competing access.
- Metadata actions often require network round trips to the file service.

**Example use case:** A render farm where dozens of machines need to access and write files in a shared directory.

### 4.3 Object storage

Object storage is accessed through an API—typically HTTP/REST—rather than being mounted as a normal filesystem in the model described by the video.

**Typical characteristics:**

- Stores complete named objects.
- Designed to scale across very large numbers of objects and storage devices.
- Useful for write-once/read-many data, large media, backups, and analytics.
- Does not provide ordinary in-place edits or general shared filesystem locking in a general-purpose bucket.
- Reads can retrieve a byte range, even though updates generally replace an object rather than editing a range in place.

### 4.4 Comparison table

| Dimension | Block storage | File storage | Object storage |
|---|---|---|---|
| How the app accesses it | Disk blocks / offsets | Files and directories | API requests using keys |
| Typical attachment model | Attached to a host | Mounted by multiple hosts | Not mounted; API-accessed |
| In-place small writes | Yes | Yes, subject to filesystem semantics | Generally no for general-purpose buckets |
| Shared access coordination | Not inherently provided by the raw block device | Filesystem server can coordinate with locks and permissions | Not equivalent to shared POSIX filesystem semantics |
| Directory hierarchy | Built above the block device by the host filesystem | Native filesystem feature | Commonly an apparent grouping of key prefixes |
| Strong fit | Databases and disk-style workloads | Shared working files/directories | Media, backups, immutable datasets, static content |
| Main trade-off | Host/attachment and coordination constraints | Network/metadata-operation overhead | Application must design around object-level updates and key-based access |

### 4.5 The useful 4 KB test

The video compares the task of changing **4 KB in the middle of a 4.2 GB file**:

- Block storage can seek to the offset and overwrite that small region.
- File storage can update the region using filesystem operations and any necessary locking.
- General-purpose object storage does not provide the same in-place edit operation, so the application typically writes a replacement object.

This is not merely “object storage is slower.” It is a difference in the operations each storage model supports.

### 4.6 A workload can use more than one storage type

A system does not have to choose exactly one storage model for every stage.

Example: a render farm may write and revise working files on shared file storage. Once a render is finalized, the finished output can be published to object storage for cheap durable storage and worldwide delivery.

**Important point:** Choose by access pattern and required semantics, not by whether the object is large or small.

---

## 5. What Happens Inside a Large Object Store?

### 5.1 Two important planes

The transcript describes an object store as multiple cooperating systems. Two conceptual parts are especially important:

1. **Index / namespace plane:** resolves the object's key and identifies where the object's data is stored.
2. **Data / storage plane:** holds the bytes on storage devices.

A read needs both: the system must first resolve where the object is, then retrieve the relevant data.

They have different failure modes:

- On the data side, a drive can fail and stored data may need to be reconstructed.
- On the index side, the service can lose or corrupt the mapping that tells it where data lives. More disks do not, by themselves, fix an incorrect index.

### 5.2 Two approaches to locating object data

The video describes two broad ways to translate a key into a storage location.

**Approach A — Look up a mapping**

- Maintain a table that maps keys to locations.
- Query that table when an object is accessed.
- Engineering challenges include scaling, availability, and maintaining the lookup system at enormous scale.

**Approach B — Compute the placement**

- Use a deterministic algorithm to calculate where an object belongs.
- The video uses Ceph's CRUSH algorithm as an example.
- Clients and storage daemons can compute placement rather than consulting a central lookup table.
- The challenge is that participants must agree on the placement map; changing the cluster layout needs careful coordination.

Both approaches solve the same basic problem—translating an object identity into a data location—but move complexity to different places.

### 5.3 Why spread data over many devices?

The transcript explains that objects are distributed across many drives so that traffic can be served by a large pool of devices in parallel.

Benefits include:

- Aggregate throughput can be much higher than what one drive can offer.
- Requests are distributed across the storage fleet.
- Large data-processing jobs can scan a very large number of objects and use parallelism.

The flip side is that individual devices will fail, so the storage system needs a durable encoding strategy and constant repair work.

### 5.4 Erasure coding and repair shards

The video illustrates durability using **erasure coding**. Rather than storing several complete copies of every object, the system splits an object into data shards and calculates additional repair shards.

Its simplified example is a 16-shard layout:

- 12 data shards.
- 4 repair shards.
- The system can reconstruct the object after losing up to four shards, assuming the encoding and failure conditions described in the example.

The core idea is that the repair shards contain enough redundancy to reconstruct missing data. The data can survive certain device failures without storing three complete copies of every object.

### 5.5 Erasure coding compared with full replication

The transcript gives this illustrative comparison:

| Strategy | Storage capacity in the example | Failure tolerance described |
|---|---:|---|
| 12 data + 4 repair shards | About 1.33× the original data size | Can survive four shard losses in the 16-shard example |
| Three full copies | About 3× the original data size | Can survive loss of two copies while one remains |

These are simplified examples rather than universal formulas for every storage configuration. Exact behavior depends on the selected encoding, placement, and failure domains.

### 5.6 Repair and integrity checking are ongoing work

Redundancy alone is not enough. If a device fails, the service needs to detect the failure and reconstruct lost redundancy before additional failures exceed the protection level.

The transcript describes background processes that:

- Detect device failures.
- Check data integrity using checksums.
- Rebuild missing shards.
- Restore redundancy after a failure.

The durability guarantee therefore depends on both the redundancy scheme and how quickly the system detects and repairs faults.

### 5.7 Durability versus availability

These terms answer different questions:

- **Durability:** Will the data continue to exist over time?
- **Availability:** Can I access the data right now?

An object may be durable yet temporarily unavailable, or may need a restore operation before it can be read from an archive class.

The video states that S3's published durability target stays the same across the classes it discusses, while availability varies. It also calls out storage classes whose data is held in a single Availability Zone.

**Important point:** A lower-cost storage class does not automatically mean the data is less durable, but it may mean a lower availability target, a restore delay, or additional retrieval costs. Check the exact class's contract before selecting it.

---

## 6. Consistency, Throughput, Key Design, and Retries

### 6.1 Strong read-after-write consistency

The video says S3 provides strong read-after-write consistency for object operations, including new objects, overwrites, and deletes. After a successful write, a subsequent read or object listing should reflect the successful operation.

The transcript dates this behavior to December 2020 and says it removed the need for older consistency workarounds.

One caveat it mentions is that some **bucket configuration** operations do not have the same immediate consistency behavior as ordinary object operations. It gives examples involving bucket deletion visibility and first-time versioning enablement.

### 6.2 Throughput comes from parallel requests

The transcript's key performance principle is:

> Object storage throughput improves by running more requests in parallel, rather than expecting one request stream to become extremely fast.

It quotes the following per-prefix figures from the video:

- At least 3,500 write requests per second per partitioned prefix.
- At least 5,500 read requests per second per partitioned prefix.

The transcript uses ten prefixes and parallel requests to illustrate how aggregate read throughput can increase. These figures are vendor-specific guidance quoted from the video; verify current limits and guidance before designing against them.

Practical implications:

- Use concurrency for large uploads and downloads where appropriate.
- Avoid relying on a single-threaded transfer for a workload that needs high throughput.
- Measure your actual client, network, and workload rather than assuming the storage service is the only limit.

### 6.3 Design keys to avoid concentrating traffic

The video explains that keys sharing the same leading prefix may share a partition's workload. A key scheme can therefore influence how evenly traffic is distributed.

Potentially problematic pattern:

```text
events/2026-10-14T12:00:00Z/file-001
 events/2026-10-14T12:00:00Z/file-002
 events/2026-10-14T12:00:00Z/file-003
```

If all newly written keys start with the same timestamp or narrow prefix, writes may concentrate on the same area of the namespace.

The transcript's guidance is to spread requests across multiple prefixes and put the varied, high-cardinality part of the key early enough to distribute requests. It notes that older blanket advice to prepend a random hash to every key is no longer the guidance it describes; follow current provider documentation for the service and bucket type you actually use.

### 6.4 Temporary throttling during scaling

The transcript says that when traffic increases, S3 scales capacity gradually rather than instantaneously. A burst may temporarily receive `503 Slow Down` responses while the service scales to the new rate.

This is why high-throughput designs should include bounded retries rather than assuming every request succeeds on the first attempt.

### 6.5 Timeouts and retries

The video's recommended client-side pattern is:

1. Set reasonable request timeouts.
2. Retry transient slowdowns or failures with an appropriate retry strategy.
3. Prefer the standard SDK retry and transfer behavior unless there is a measured reason to customize it.
4. Keep retries bounded and account for their request cost.

Why retries may help: a slow request could be caused by one temporarily slow path through a distributed system. A retry can take another path and finish sooner.

The transcript describes a repeated write of the same bytes to the same key as safe because a single-key write is atomic. Applications should still understand their versioning and request semantics before building retry logic, and should avoid allowing retries to create unintended application-level side effects.

---

## 7. Practical Pattern: Let the Client Upload Directly

### 7.1 The problem with proxying every upload through your API server

Imagine a user uploads a 4.2 GB video. If all bytes pass through the application's API server, the server must receive and forward the entire payload even though it does not need to process the bytes itself.

That creates unnecessary work and resource use for the API tier.

### 7.2 Presigned URLs

A **presigned URL** gives a client time-limited permission to perform a specific object operation without giving that client general cloud credentials.

Typical flow:

1. Client asks the application's API for permission to upload.
2. The server authenticates and authorizes the request.
3. The server generates a presigned URL.
4. Client uploads directly to object storage using that URL.
5. The application reacts to the completed upload, for example by processing an event.

The application server remains in the **authorization path**, but the file bytes do not have to travel through it. This is a key scalability pattern for large file uploads.

### 7.3 Security of presigned URLs

The transcript emphasizes that a presigned URL behaves like a bearer token: **whoever has the URL can use the permission it grants until it expires**, subject to the signing credentials and URL constraints.

Therefore:

- Do not expose presigned URLs publicly unless that is intentional.
- Choose an expiry period appropriate to the operation.
- Treat the URL like a secret credential.
- Remember that temporary signing credentials can expire before a longer URL expiry would otherwise suggest.

### 7.4 Multipart uploads

A large upload can be divided into multiple independently uploaded parts. The transcript outlines three steps:

1. **Initiate** the multipart upload.
2. **Upload parts** independently; failed parts can be retried without retransmitting successful parts.
3. **Complete** the upload to assemble/commit the object.

Example from the video: a 4.2 GB video is uploaded as many 100 MB parts. The exact part count and size are illustrative.

Benefits:

- Failed parts can be uploaded again independently.
- Parts can be uploaded in parallel.
- A network interruption does not necessarily require restarting the whole file.
- Large uploads can make better use of available network throughput.

### 7.5 Remember to clean up incomplete multipart uploads

An upload that is initiated but never completed or stopped can leave billable parts behind. The transcript notes that abandoned multipart uploads may not show up in an ordinary object listing and recommends lifecycle cleanup for incomplete uploads.

**Important point:** A multipart workflow must include a completion/abort path and a cleanup policy. Do not assume unfinished parts automatically disappear immediately.

---

## 8. Events, Notifications, and Idempotent Processing

### 8.1 Object storage can notify downstream systems

S3 event notifications can be used to trigger work when an object is created or when certain other events occur, such as removal, restoration, replication, or lifecycle transitions.

The transcript names integration destinations including:

- Amazon SNS.
- Amazon SQS.
- AWS Lambda.
- Amazon EventBridge.

Example: when a new video is uploaded, the bucket emits an event that wakes a transcoding workflow.

### 8.2 At-least-once delivery

The video says event notifications are designed for **at-least-once delivery**. In practical terms, the consumer may receive the same logical event more than once.

Your event handler should therefore be **idempotent**: processing the same event repeatedly should not produce duplicate or corrupt results.

Examples of defensive design:

- Record a stable event/object identifier that has already been processed.
- Make output keys deterministic where appropriate.
- Check processing state before doing expensive work.
- Ensure retries do not charge a customer or publish duplicate business actions unintentionally.

### 8.3 Avoid a self-triggering loop

A common trap is configuring a function to run when an object is written to a bucket, then having that function write a result back into the same triggering bucket. The function's own output may trigger it again.

The transcript gives two ways to avoid this pattern:

- Use separate input and output buckets.
- Filter the notification to a particular prefix so the function ignores its own output path.

---

## 9. Reading Ranges and Downloading Large Objects Efficiently

### 9.1 Range reads

An HTTP range request retrieves a specified byte range from an object rather than downloading the entire object.

Example conceptually:

```text
Object size: 4.2 GB
Requested bytes: 0–1 MB
Result: only that selected byte range
```

The object stays whole and immutable, but the client can read selected slices.

The transcript notes a limitation: its described S3 `GetObject` range behavior does not allow multiple disjoint ranges in a single GET request. Multiple separate range requests can be issued when multiple ranges are needed.

### 9.2 Where range reads help

- A video player can fetch the portion needed for playback.
- A columnar data reader can fetch a file footer and only the relevant data blocks.
- A service can inspect a header or part of a file without transferring the entire object.

For example, a Parquet reader can inspect metadata, determine which row groups it needs, and request only the corresponding byte ranges.

### 9.3 Parallel range downloads

If the application genuinely needs the entire large object, it can request different ranges in parallel, then reassemble them on the client.

This is the download-side analogue of multipart upload:

- Multipart upload: split a large object into parts for uploading.
- Parallel range download: split a large object into byte ranges for reading.

Parallel transfers can raise throughput, but the limit may then shift to the client CPU, memory, network card, connection management, or reassembly code. The transcript notes that SDK transfer managers already implement parallel transfer behavior, so prefer them to a hand-rolled single-stream download unless measurements justify a custom solution.

---

## 10. Finding Huge Numbers of Objects: Listing vs. Inventory

### 10.1 Why repeatedly listing is expensive at scale

The transcript says a list request returns at most 1,000 keys at a time. Therefore, listing 200 million objects would require about 200,000 paginated list calls, before considering retries or other work.

This is not a good way to run frequent broad scans over an enormous bucket if a scheduled inventory will do.

### 10.2 S3 Inventory

**S3 Inventory** is described as a scheduled report containing object keys and metadata. It can produce files in formats such as:

- CSV.
- ORC.
- Parquet.

The report can then be queried or processed using tools such as Athena or Spark.

Advantages:

- It avoids repeatedly enumerating the bucket through the list API.
- It separates large-scale discovery from live object requests.
- It provides a dataset that can be analyzed with data-processing tools.

Trade-off:

- Inventory is not necessarily current to the second. The transcript describes the report as eventually consistent, says recent changes may be missing, and notes that the initial report can take up to 48 hours.

For decisions requiring current state, the video recommends validating the row against the object with a `HEAD` request before acting.

**Rule of thumb:** Use live object operations when you need current state; use inventory when you need to analyze or enumerate very large collections efficiently.

---

## 11. Updating Data Safely: Immutable Objects and Pointer Swaps

### 11.1 Write new data, then change a pointer

Because object contents are not normally edited in place, the transcript recommends a pattern:

1. Write the new object under a new key.
2. Verify that the new object is complete and ready.
3. Atomically update a small pointer or metadata reference to point at the new object.
4. Retain the previous object until it is safe to remove it.

The pointer might be a database row or a metadata file that tells readers which version is current.

### 11.2 Why this pattern is safer

- Readers already using the previous object are not interrupted by a partial rewrite.
- A failed new write can leave an unused/orphaned object rather than corrupting the current object.
- A rollback may be as simple as pointing back to the prior object.
- A single atomic pointer update can represent the transition from one complete version to another.

### 11.3 Apache Iceberg example

The transcript uses Apache Iceberg to demonstrate this approach. Table state is represented by metadata files. Instead of editing an existing metadata file in place, an update writes new metadata and switches the table to the new metadata reference atomically.

This illustrates a general design principle:

> Keep large data files immutable; make a small, controlled change to the reference that identifies the current state.

The transcript also mentions conditional writes as a mechanism for making pointer changes safer by checking assumptions during the write. The exact conditional-write mechanism should be chosen according to the current API and application's concurrency requirements.

---

## 12. Global Delivery: CDN, Transfer Acceleration, and Replication

### 12.1 Use a CDN to serve users from nearby locations

A **Content Delivery Network (CDN)** places cached copies of content at edge locations near users.

Basic flow:

1. A viewer requests an object.
2. If the CDN has a cached copy, it can return that copy directly.
3. On a cache miss, the CDN obtains the object from the origin and may cache it for later requests.

Benefits highlighted in the video:

- Lower latency for users far from the bucket's region.
- Fewer requests reaching the origin when the content is cached.
- Potential reductions in origin traffic and total transfer cost, depending on the provider's pricing model.

The transcript gives approximate origin first-byte latency and specific CloudFront billing statements. Those precise figures and billing conditions should be checked against current pricing and architecture documentation.

### 12.2 Keep compute near the bucket

If a transcoder needs to read a large object, placing the compute close to the bucket's region avoids moving the entire large file across a region boundary unnecessarily.

The video frames distance as a cost in both latency and transfer charges. The practical pattern is:

- Put the data-processing compute near the primary bucket.
- Move or cache content closer to clients when the client is far away.

### 12.3 S3 Transfer Acceleration

The transcript describes **S3 Transfer Acceleration** as an option for clients uploading to one central bucket from distant locations.

Conceptually:

1. The client uploads to a nearby edge entry point.
2. The data travels over the provider's optimized network path toward the bucket's region.
3. The final object still lands in the selected bucket/region.

This is aimed at reducing the distance-related cost for remote uploads. The transcript notes that it has separate transfer charges and offers less benefit when the client is already close to the bucket.

### 12.4 Same-region and cross-region replication

Replication rules copy new object versions asynchronously from a source bucket to another destination bucket. The transcript describes two patterns:

- **Same-Region Replication (SRR):** source and destination are in the same region.
- **Cross-Region Replication (CRR):** the destination is in another region.

Potential uses include:

- Maintaining another copy in a separate account for protection.
- Placing a replica nearer to a user population.
- Keeping a cold copy for retention or recovery purposes.
- Supporting recovery from a regional disruption.

The transcript says the destination buckets need versioning enabled and that metadata and version details travel with replicated objects.

### 12.5 Replication is asynchronous

Do not treat replication as an instantaneous transaction. The source write may succeed before the destination replica exists.

Consequences:

- An immediate read from the destination may not find the new object yet.
- Large objects may take much longer to arrive than small ones.
- Applications must account for replication lag if users can be routed between regions.

The video also says a deletion of a specific source version does not automatically delete that version at the destination, and lifecycle actions stay local to each bucket. Treat the exact replication and delete semantics as configuration-dependent details that should be checked before relying on them.

### 12.6 Multi-Region Access Point versus replication

The transcript distinguishes two responsibilities:

- **Replication rules** move object versions between buckets and help keep copies in sync over time.
- **A Multi-Region Access Point** gives clients a common global endpoint and routes requests to an appropriate active bucket.

A global endpoint does **not**, by itself, synchronize buckets. If two regions need the same objects, replication is a separate part of the design.

### 12.7 Example architecture

```text
Client uploads
     |
     | presigned URL / optional acceleration
     v
Primary object bucket  ---- event notification ----> Processing worker
     |                                               |
     |                                               v
     |                                         Output object
     |
     +---- CDN / edge cache ----------------------> Worldwide viewers
     |
     +---- replication ----> Second-region bucket
     |
     +---- replication ----> Separate-account recovery/vault bucket
```

This is a conceptual picture of the patterns in the transcript, not a requirement that every system use all of them.

---

## 13. Understanding the Cost Model

### 13.1 Four separate cost categories

The transcript advises thinking of the bill as four independent meters:

1. **Storage:** how much data is retained and in which storage class.
2. **Requests and retrievals:** how often APIs are called and whether the class charges to retrieve data.
3. **Data transfer:** how much data is transferred and where it goes.
4. **Management features:** costs for extra capabilities such as inventory, replication, or other management services where applicable.

The exact bill depends on current regional pricing, request mix, transfer paths, object sizes, and the selected features.

### 13.2 Access pattern can matter more than volume

Two workloads can both store one terabyte and have very different costs:

- Workload A reads the terabyte once a year.
- Workload B reads it millions of times a day and serves those bytes to end users.

Storage capacity alone does not describe the request and transfer costs. Before selecting a cheaper storage class, estimate how often data will be read, how quickly it must be retrieved, and whether it must be transferred across regions or to external clients.

### 13.3 Storage class is also a retrieval-time choice

The transcript arranges the classes discussed into a retrieval-time ladder:

| Class mentioned in the video | Retrieval behavior described in the transcript |
|---|---|
| S3 Standard | Milliseconds |
| S3 Standard-IA | Milliseconds, with infrequent-access economics and constraints |
| S3 Glacier Instant Retrieval | Milliseconds |
| S3 Glacier Flexible Retrieval | Expedited retrieval described as typically 1–5 minutes; standard 3–5 hours; bulk 5–12 hours |
| S3 Glacier Deep Archive | Approximately 12–48 hours |
| S3 Intelligent-Tiering archive tiers | Some archive tiers require restoring a temporary copy before reading |

These are the retrieval times quoted in the supplied video, not a replacement for current service documentation.

### 13.4 Archived data may need a restore before it can be read

For the archive classes discussed, the transcript explains that the object may still exist durably but be unavailable for immediate direct reading. A restore creates a temporary readable copy for a requested period; it does not necessarily move the original object permanently into a faster class.

This can mean paying for both the archived object and the temporary restored copy while the copy exists. If an object must remain in a faster class, the transcript says the application can copy it and change its storage class rather than relying only on a temporary restore.

### 13.5 Lifecycle rules

A lifecycle configuration automates actions on objects based on rules. The transcript distinguishes two action types:

- **Transition:** move an object to another storage class after a configured condition or age.
- **Expiration:** expire/delete an object after a configured condition or age.

Important behavior described in the video:

- Rules can affect objects that already exist, not only future uploads.
- A newly added rule may therefore apply to old objects that already meet its conditions.
- Lifecycle transitions/deletions are not prevented simply by denying user operations in a bucket policy, according to the transcript.

Before enabling a broad lifecycle rule, examine which existing objects match it and make sure the transition or expiration behavior is intended.

### 13.6 Intelligent-Tiering as an alternative

The transcript describes Intelligent-Tiering as an option that can move objects between tiers based on access behavior, with a small per-object monitoring fee and no retrieval fees as characterized by the video.

It trades some monitoring cost and service-managed behavior for not having to predict access frequency perfectly for every object.

It is not automatically the cheapest choice for every workload: compare the current fees and the access pattern with explicit lifecycle policies.

### 13.7 Minimum object sizes and minimum storage durations

A low per-gigabyte rate can be misleading when other billing rules apply. The transcript calls out:

- A minimum billable object size of **128 KB** for the infrequent-access and Glacier Instant classes it discusses.
- Minimum storage durations of **30, 90, or 180 days**, depending on the class.
- Retrieval charges in some classes.
- Additional per-object metadata overhead for Glacier Flexible Retrieval and Deep Archive, described in the transcript as 40 KB per archived object.

The example in the video is a million 20 KB thumbnails. If each object is billed at a 128 KB minimum, plus archive metadata overhead and minimum-duration fees, the cheapest per-gigabyte tier may become the more expensive overall choice.

**Design lesson:** Very small objects can be a poor fit for cold archive classes. Consider object count, average object size, retention duration, retrieval frequency, and restore charges—not just the headline storage price.

---

## 14. Versioning, Object Lock, and Delete Markers

### 14.1 Object versioning

With versioning enabled, writing a new version to the same key can leave older versions stored. This can support recovery from unintended overwrites or deletions, but it can also increase storage costs because old versions remain stored until removed by an appropriate operation or lifecycle rule.

A key and an object version are not the same thing:

- **Key:** the logical name used to identify the object location.
- **Version:** a specific stored generation of the object under that key.

### 14.2 Object Lock and WORM retention

The transcript describes Object Lock as supporting a **write once, read many (WORM)** retention model and says it requires versioning to be enabled.

Two retention modes are covered:

**Compliance mode**

- A protected object version cannot be overwritten or deleted during its retention period, including by the account root user, as described in the video.
- The retention period cannot simply be shortened by an administrator.
- It is for strict retention requirements where even powerful administrators must not be able to remove protected data early.

**Governance mode**

- A specially authorized user can bypass retention when the required permission and explicit request behavior are used.
- It is more flexible than compliance mode but still provides retention controls.

**Legal hold**

- Has no fixed expiration date in the model described.
- Remains in effect until an authorized person removes it.

These features are powerful and potentially irreversible in their consequences. Configure retention mode, period, and permissions carefully and verify the current service rules before enabling them for production data.

### 14.3 Retention applies to a version, not necessarily the key name

A locked version does not mean nothing else can happen at that key. The transcript explains that new versions or delete markers may be created above a protected version, while the protected version itself remains retained.

As a result, the key can appear deleted to an ordinary reader even though a locked version remains stored underneath it.

### 14.4 Delete markers in a versioned bucket

In the transcript's versioning example, a normal delete creates a **delete marker** as the current version rather than physically removing all previous object versions.

Consequences:

- A normal GET without a version ID can behave as if the object is deleted.
- A standard listing may not show the key as a current object.
- Old versions still occupy storage and may still be billed.
- A normal-looking empty bucket can still contain many noncurrent versions hidden from a regular listing.

### 14.5 Cleaning up old versions

The transcript points to lifecycle rules that expire noncurrent versions as a way to prevent old versions from accumulating indefinitely.

A sound cleanup design should distinguish among:

- Expiring the current object.
- Expiring noncurrent versions.
- Removing incomplete multipart uploads.
- Retaining versions protected by Object Lock.

Do not assume that making an object disappear from an ordinary list automatically removes its stored bytes or stops storage charges.

---

## 15. End-to-End Example: A Video Platform

The video uses one 4.2 GB clip to connect many of the ideas. A practical flow based on its patterns could look like this:

1. **Upload authorization:** The creator asks the application for permission to upload. The application returns a short-lived presigned URL.
2. **Direct upload:** The client sends the bytes straight to object storage instead of proxying all bytes through the API server.
3. **Multipart transfer:** The client uploads parts independently and retries only failed parts. An incomplete-upload lifecycle rule cleans up abandoned parts.
4. **Upload event:** The bucket publishes an event when the object is created. The event consumer is designed to handle duplicate deliveries safely.
5. **Processing:** A transcoder runs close to the bucket, avoiding unnecessary cross-region movement of the source video.
6. **Range reads:** The processor reads only the ranges it needs for initial inspection. If it needs the full file, it can use parallel range downloads.
7. **New output:** Transcoded output is written as a new object instead of editing the original object in place.
8. **Pointer swap:** Application metadata is updated to mark the new output as current. Readers can continue using the old completed object until the pointer changes.
9. **Global playback:** A CDN caches popular output near viewers and reduces repeated origin traffic.
10. **Remote ingestion:** If upload clients are far from the bucket region, Transfer Acceleration may be considered after evaluating its charges.
11. **Resilience:** Replication creates additional copies in another region and/or a separate account. A global endpoint can direct client requests, while replication rules separately move data between regions.
12. **Cost control:** Lifecycle rules move infrequently accessed data to a suitable storage class and expire data or old versions when retention permits.
13. **Compliance:** Object Lock may be applied to versions that must be retained under specific requirements.
14. **Deletion and audit:** The team checks version listings and lifecycle policies so that delete markers and noncurrent versions do not silently accumulate storage charges.

The important insight is not that every media platform needs every feature. It is that each pattern addresses a distinct operational requirement: upload scale, reliable processing, partial reads, global latency, disaster recovery, retention, or cost.

---

## 16. A Practical Decision Framework

Use these questions in order when choosing storage for a workload.

### Question 1: Does the application need to modify small parts of the data in place?

- **Yes, frequently and at known offsets:** consider block storage.
- **Yes, through normal file operations:** consider file storage.
- **No, objects are mostly written complete and later read:** object storage may be a good fit.

### Question 2: How many machines need access to the same data at once?

- **Primarily one host attached to a disk volume:** block storage may fit.
- **Many hosts need a shared directory with permissions and coordination:** file storage may fit.
- **Clients access objects through HTTP/API calls:** object storage may fit.

### Question 3: Does the application need filesystem semantics?

If the application expects directories, rename-in-place behavior, file locks, and POSIX-like permissions, a file service is usually a more natural fit than treating an object bucket like a mounted filesystem.

### Question 4: Does the application read the whole object or selected ranges?

Object storage can be efficient for selected byte ranges as well as whole objects. Consider the pattern of reads and whether parallel range requests can improve throughput.

### Question 5: What are the durability, availability, and recovery requirements?

Decide whether the design needs multiple Availability Zones, another region, a separate-account copy, archive retention, versioning, or Object Lock. Do not treat CDN caching as a substitute for a durable recovery copy.

### Question 6: What does access actually cost?

Estimate all relevant charges:

- Stored GB-months by class.
- API request counts.
- Retrieval operations and restore requirements.
- Data transfer between regions and to users.
- Replication, inventory, monitoring, and other management features.
- Minimum object sizes and minimum storage-duration rules.

### Example decisions from the transcript

| Workload | Important access characteristic | Storage choice in the video |
|---|---|---|
| PostgreSQL data volume | One host, frequent small in-place writes at known offsets | Block storage |
| Shared render directory | Many machines access and write files concurrently; locking matters | File storage |
| Finished media library | Written once, read worldwide, not edited in place | Object storage, commonly paired with a CDN |
| Render farm workflow | Mutable working files followed by published immutable output | File storage for work; object storage for finished output |

**The main rule:** Decide based on the required access semantics and attachment model—not simply on object size.

---

## 17. Common Misconceptions to Avoid

- **“The slashes mean there are real folders.”** In a general-purpose bucket, prefixes create a folder-like view; the namespace is flat.
- **“Renaming an object is just a metadata change.”** The general-purpose-bucket pattern described in the video is copy plus delete.
- **“Object storage can edit a few bytes in place.”** It generally cannot do this in the way a block device or filesystem can.
- **“I can query any object attribute directly in the bucket.”** The key/prefix/listing model is not the same as a queryable secondary index. Store searchable attributes separately or use inventory/analytics where suitable.
- **“Durability and availability mean the same thing.”** Durability concerns whether the data still exists; availability concerns whether it can be accessed now.
- **“A successful object write is not immediately visible.”** The transcript describes strong read-after-write consistency for object operations, while distinguishing some bucket-configuration behavior.
- **“One stream is enough for maximum throughput.”** Parallel requests and transfers are central to the video's performance guidance.
- **“A successful event notification is delivered exactly once.”** The transcript describes at-least-once delivery, so consumers must be idempotent.
- **“A cheap storage rate guarantees a cheap bill.”** Requests, transfer, retrieval fees, minimum object sizes, and minimum storage durations can dominate.
- **“Deleting a key means all its bytes have been removed.”** In a versioned bucket, a delete marker can hide the current object while older versions remain stored and billed.
- **“A Multi-Region Access Point replicates data.”** The transcript separates routing from replication; replication rules keep copies moving between buckets.
- **“Pick block, file, or object storage based on file size.”** Access behavior and required semantics are more predictive than size.

---

## 18. Glossary

| Term | Plain-language meaning |
|---|---|
| **Object** | A named unit of stored data plus descriptive information. |
| **Bucket** | A named collection/namespace for objects. |
| **Key** | The string used to address an object. |
| **Version** | A particular stored generation of an object under a key. |
| **Metadata** | Descriptive properties associated with the object, such as content type or length. |
| **Tag** | A changeable label attached to an object. |
| **Prefix** | The beginning portion of a key used for grouping or filtering listings. |
| **Block storage** | Storage addressed as blocks/offsets, commonly used like a disk. |
| **File storage** | Storage that exposes files and directories with filesystem semantics. |
| **Object storage** | API-accessed storage where data is addressed by object keys. |
| **Namespace / index plane** | The part of the service that resolves a key to the object's location. |
| **Data plane** | The part of the service that stores and serves the object's bytes. |
| **Shard** | One piece of a larger encoded object. |
| **Erasure coding** | A redundancy technique that stores data shards plus repair shards. |
| **Durability** | The likelihood/guarantee that stored data continues to exist. |
| **Availability** | The degree to which data can be accessed when needed. |
| **Read-after-write consistency** | A successful write is visible to a subsequent read under the specified consistency model. |
| **Presigned URL** | A time-limited URL authorizing a particular operation on an object. |
| **Multipart upload** | Uploading one large object as independently transferable parts. |
| **Range request** | Requesting a selected byte range rather than the whole object. |
| **Idempotent processing** | Repeating an operation has no unintended additional effect. |
| **S3 Inventory** | A scheduled report listing objects and selected metadata. |
| **CDN** | A network of edge locations that cache and deliver content nearer to users. |
| **Transfer Acceleration** | A service pattern for improving distant clients' upload path to a central bucket. |
| **Replication** | Asynchronously copying objects/versions to another bucket. |
| **Lifecycle rule** | An automated rule that transitions or expires objects based on conditions such as age. |
| **Object Lock** | Retention controls that protect object versions against deletion or overwrite for a defined period or legal hold. |
| **Delete marker** | A marker that can make an object appear deleted in a versioned bucket without removing prior versions. |

---

## 19. Quick Revision Sheet

Remember these points before a system-design interview:

1. **Object storage is a key-to-object map.** The key is the main address; a prefix is not automatically a real folder.
2. **General-purpose object updates are whole-object oriented.** Metadata changes, renames, and replacements can involve copies rather than in-place edits.
3. **Use tags for changeable labels.** Use separate database/index structures when you need rich queries over object attributes.
4. **Block, file, and object storage expose different semantics.** Block supports disk-style access; file storage supports shared filesystem behavior; object storage scales through API-based object access.
5. **Inside the store, locating data and storing bytes are separate problems.** Object placement and redundancy make large-scale storage possible.
6. **Erasure coding creates repair information.** Durability depends on redundancy plus timely failure detection and repair.
7. **Durability is not availability.** Archived data can remain durable while requiring a restore before reading.
8. **Object writes are strongly read-after-write consistent according to the transcript.** Do not confuse that with every bucket-configuration operation.
9. **Throughput comes from parallel requests.** Avoid hot key-prefix patterns, handle transient slowdowns, and use SDK transfer facilities where appropriate.
10. **Use presigned URLs and multipart uploads for large client uploads.** Keep the API server out of the file-byte path and clean up abandoned uploads.
11. **Treat event notifications as at-least-once.** Make consumers idempotent and prevent self-triggering loops.
12. **Use range reads for slices and parallel ranges for large downloads.** Do not retrieve more bytes than the workload needs.
13. **Use inventory for huge scheduled enumeration.** Use live operations and validation when current state matters.
14. **Prefer immutable data plus pointer swaps for safe updates.** It helps readers, rollback, and failure recovery.
15. **A CDN improves global delivery; acceleration helps distant uploads; replication creates another copy.** These solve different problems.
16. **Calculate the full bill.** Include storage, requests/retrieval, transfer, management features, size minimums, and minimum durations.
17. **Lifecycle rules automate transitions and expiration.** Understand their effect on existing objects and retained versions.
18. **Object Lock protects versions.** Compliance, governance, and legal holds have different control behavior.
19. **Versioned deletion may create a marker rather than remove old versions.** Noncurrent versions can continue to incur storage charges.
20. **Choose storage based on access pattern and attachment model—not data size.** A workload can use different storage types for different stages.

---

## 20. Self-Test Questions

Try answering these without looking at the sections above.

1. What are the main components of an object, and what uniquely addresses it?
2. Why are the apparent folders in a general-purpose bucket not equivalent to filesystem directories?
3. What is the difference between object metadata and object tags?
4. Why can renaming a large object be costly?
5. Why might a separate database be needed beside an object bucket?
6. What is the main difference between block, file, and object storage?
7. What do the index plane and data plane each do?
8. How does erasure coding help an object survive device failure?
9. Explain durability versus availability in your own words.
10. Why is parallel request execution important for object-storage throughput?
11. What is a hot prefix, and how can key design contribute to it?
12. How does a presigned URL let a client upload directly while keeping authorization in the application?
13. Why does a consumer of object-created events need to be idempotent?
14. When would a byte-range request be preferable to downloading an entire object?
15. When is inventory more suitable than repeatedly listing every object?
16. Explain the “write a new object, then switch a pointer” update pattern.
17. What is the difference between a CDN, transfer acceleration, and replication?
18. Name the four broad cost categories described in the video.
19. Why can a very cheap archive class be expensive for millions of tiny objects?
20. What is a delete marker, and why might a versioned bucket still incur storage costs after a delete?
21. What do Object Lock compliance mode, governance mode, and legal hold mean in the transcript?
22. Why is object size alone a poor rule for choosing a storage system?

---

## Final Takeaway

The central idea in the video is simple: **object storage is a scalable collection of named, mostly immutable objects, addressed primarily by key**. Its architecture makes it excellent for large collections of durable data and global content delivery, but it places responsibility on the application to design keys, parallelize transfers, maintain indexes where needed, process notifications safely, manage lifecycle and versions, and account for retrieval and transfer costs.

Choose block storage when disk-style in-place access is essential, file storage when multiple machines need shared filesystem semantics, and object storage when complete objects can be stored and accessed through an API. For complex systems, combine them where each is strongest.
