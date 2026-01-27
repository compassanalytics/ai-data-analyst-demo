# Databricks Free Tier and Workshop Setup Guide

**Research Date:** January 26, 2026
**Purpose:** Comprehensive guide for setting up hands-on Databricks workshops using free/trial tier options

---

## Executive Summary

As of January 2026, Databricks offers two primary free options for workshop environments:

1. **Databricks Free Edition** - Perpetual, no-cost access with daily quotas (replaces Community Edition which was retired on January 1, 2026)
2. **14-Day Free Trial** - $400 in credits for full platform access

For a workshop with 40-50 participants, the recommended approach depends on your specific needs:
- **Free Edition**: Best for learning-focused workshops where each participant creates their own account
- **14-Day Trial + Enterprise Setup**: Better for production-like environments requiring centralized control

---

## 1. Databricks Community Edition Status

### IMPORTANT: Community Edition Has Been Retired

**Community Edition was officially retired on January 1, 2026.** All users have been encouraged to migrate to the new **Databricks Free Edition**.

Key changes from Community Edition to Free Edition:
- Free Edition uses **serverless compute only** (no classic clusters)
- **Scala and RDDs are not supported** (Python and SQL only)
- **Unity Catalog is included** (major upgrade from CE)
- Modern features like MLflow, Delta Live Tables, Dashboards, and AI Assistant are available
- Cloud mounts (DBFS mounts) are not supported

**Migration Path:** Users with Community Edition accounts can migrate with a one-click tool at [login.databricks.com](https://login.databricks.com) or create fresh Free Edition accounts at [signup.databricks.com](https://signup.databricks.com).

**Sources:**
- [Community Edition Retirement Announcement](https://community.databricks.com/t5/announcements/psa-community-edition-retires-at-the-end-of-2025-move-to-free/td-p/141888)
- [Guide: Moving from Community Edition to Free Edition](https://community.databricks.com/t5/databricks-university-alliance/guide-and-best-practices-moving-from-community-edition-to-free/ta-p/129308)

---

## 2. Databricks Free Edition - Current Features and Limitations

### Features Included

| Feature | Availability |
|---------|--------------|
| Python notebooks | Yes |
| SQL notebooks | Yes |
| Unity Catalog | Yes |
| Serverless compute | Yes (managed by Databricks) |
| Databricks Assistant (AI) | Yes |
| MLflow | Yes |
| Delta Live Tables | Yes (1 active pipeline per type) |
| Dashboards | Yes |
| Model Serving | Yes (CPU only, limited) |
| Genie | Yes |
| Jobs/Workflows | Yes (max 5 concurrent tasks) |
| SQL Warehouse | Yes (1 warehouse, 2X-Small max) |
| Vector Search | Yes (1 endpoint, 1 unit) |
| Databricks Apps | Yes (1 app, auto-stops after 24 hours) |

### Limitations

#### Compute Restrictions
- **Serverless only** - No custom cluster configurations
- **No GPUs** - CPU-only workloads
- **Small cluster sizes** - Limited to small serverless compute
- **One all-purpose cluster** (CPU-only)
- **One SQL warehouse** capped at 2X-Small size
- **Max 5 concurrent job tasks** per account

#### Language/Feature Restrictions
- **No Scala support**
- **No R support**
- **No RDD APIs** - Only Spark DataFrame/SQL APIs via Spark Connect
- **No JAR libraries** in notebooks (JAR tasks in jobs are supported)
- **No cloud mounts** - Cannot mount external storage
- **Limited DBFS access** - Use Unity Catalog volumes or workspace files instead
- **Restricted outbound internet** - Limited to trusted domains only

#### Administrative Limitations
- **One workspace per account**
- **One metastore per account**
- **No account console access**
- **No account-level APIs**
- **No SSO/SCIM** - Only email OTP, Google, or Microsoft sign-in
- **Cannot be Marketplace providers**

#### Unsupported Features
- Online tables
- Clean rooms
- Agent Bricks
- Lakebase database instances
- Legacy features
- Provisioned throughput for model serving

#### Usage Policies
- **Non-commercial use only**
- **No SLA or official support**
- **Inactive accounts may be deleted** after prolonged inactivity
- Contact: free_edition_help@databricks.com

**Sources:**
- [Databricks Free Edition Limitations (AWS)](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
- [Databricks Free Edition Limitations (Azure)](https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-edition-limitations)

---

## 3. Free Trial Options

### 14-Day Free Trial with $400 Credits

| Aspect | Details |
|--------|---------|
| Duration | 14 days |
| Credits | Up to $400 in Databricks usage |
| Platform | Full Databricks platform access |
| Cloud Providers | AWS, Azure, GCP |
| Billing | Pay-as-you-go after trial ends |

#### What's Included in the Trial
- Full access to all Databricks features
- Premium tier features (on Azure)
- Custom cluster configurations
- GPU compute (subject to availability)
- All language support (Python, SQL, Scala, R)
- Full administrative capabilities
- Unity Catalog
- Account console access

#### Personal Email Limitations
If signing up with a personal email address (Gmail, Yahoo, etc.):
- Serverless SQL warehouses capped at 50 DBUs/hour (max one per workspace)
- Notebook and job compute limited to 50 DBUs/hour
- No GPU access
- Vector search restricted to one endpoint at 1 unit
- Limited external network connectivity

**Recommendation:** Use a business/corporate email to avoid these restrictions.

#### Trial Signup Options

1. **Express Signup** - No cloud account needed, immediate serverless workspace
2. **AWS Marketplace** - Integrates with existing AWS billing
3. **Azure Portal** - Create workspace with Trial (Premium) pricing tier
4. **GCP Console** - Standard signup process

#### After Trial Ends
- Automatic conversion to pay-as-you-go
- To avoid charges: terminate all compute, remove payment methods, cancel subscription

**Sources:**
- [Databricks Free Trial (AWS)](https://docs.databricks.com/aws/en/getting-started/free-trial)
- [Databricks Free Trial (Azure)](https://learn.microsoft.com/en-us/azure/databricks/getting-started/free-trial)
- [Try Databricks Free](https://www.databricks.com/try-databricks)

---

## 4. What's Included vs. Excluded Comparison

| Feature | Free Edition | 14-Day Trial |
|---------|--------------|--------------|
| **Cost** | Free forever | $400 credits (14 days) |
| **Unity Catalog** | Yes | Yes |
| **Python/SQL** | Yes | Yes |
| **Scala/R** | No | Yes |
| **RDD APIs** | No | Yes |
| **GPUs** | No | Yes |
| **Custom Clusters** | No | Yes |
| **Serverless Compute** | Yes | Yes |
| **Admin Console** | No | Yes |
| **SSO/SCIM** | No | Yes |
| **Multiple Workspaces** | No (1 only) | Yes |
| **Commercial Use** | No | Yes |
| **SLA/Support** | No | Yes (during trial) |
| **Cloud Mounts** | No | Yes |
| **Classic Compute** | No | Yes |
| **Jobs** | 5 concurrent max | Full capabilities |
| **SQL Warehouse Size** | 2X-Small max | Any size |

---

## 5. Workshop Environment Setup Best Practices

### For Free Edition Workshops (40-50 Participants)

#### Setup Approach
Since Free Edition requires **individual accounts per user**, the recommended setup is:

1. **Pre-workshop Communication**
   - Send signup instructions 1-2 days before the workshop
   - Provide link: [signup.databricks.com](https://signup.databricks.com)
   - Request participants create accounts using their email addresses
   - Share a video walkthrough of the signup process

2. **Account Configuration**
   - Each participant gets their own workspace
   - No centralized admin control possible
   - Participants manage their own environments

3. **Content Distribution Options**
   - **Option A (Recommended):** Create a Databricks Marketplace listing for your workshop datasets and notebooks
   - **Option B:** Host notebooks on GitHub, have participants import via URL
   - **Option C:** Provide downloadable notebook archives (.dbc files)

4. **Daily Quota Management**
   - 99% of users will not hit rate limits under normal use
   - If quotas are exceeded, compute pauses until next day reset
   - Plan multi-day workshops to spread compute usage
   - Avoid having all 40-50 participants run heavy workloads simultaneously

#### Important Considerations
- **No shared workspaces** - Each account is isolated
- **Cannot pre-provision accounts** - Students must self-register
- **No instructor monitoring** - Cannot see participant progress centrally
- **Language restrictions** - Ensure all materials use Python/SQL only

### For 14-Day Trial Workshops (Enterprise Setup)

If you need centralized control and full features:

1. **Option A: Individual Trial Accounts**
   - Each participant signs up for their own trial
   - Similar to Free Edition but with full features
   - Participants use their own $400 credits
   - Risk: Participants may need to provide payment info

2. **Option B: Organizational/Partner Setup**
   - Contact Databricks for workshop credits
   - Use enterprise workspace with multiple users
   - Centralized admin control
   - Requires Databricks partnership or sales engagement

3. **Option C: Third-Party Lab Platforms**
   - **CloudLabs + Databricks**: Managed lab environments with instructor controls
   - **Vocareum**: Pre-provisioned sandbox environments
   - **Databricks Academy Labs**: Guided lab experiences (limited availability)

### Enterprise/Partner Workshop Setup

For professional workshops with full control:

1. **Databricks Academy Labs**
   - Guided lab experiences
   - Available through partner programs
   - Access via Partner Labs enrollment

2. **CloudLabs Integration**
   - Custom lab duration and cluster runtime
   - Pre-installed libraries
   - Instructor dashboards for monitoring
   - Can host on AWS, Azure, or GCP
   - Catalog and permission management

3. **Manual Enterprise Setup**
   - Create dedicated workspace for workshop
   - Use cluster policies to limit resource consumption
   - Set up user groups via Identity Provider
   - Pre-load datasets to shared storage
   - Use ARM templates or Terraform for provisioning

**Sources:**
- [CloudLabs Databricks Lab Quick Start Guide](https://cloudlabs.ai/blog/cloudlabs-databricks-lab-quick-start-guide/)
- [Databricks Academy Labs](https://www.databricks.com/databricks-academy-labs)
- [5 Best Practices for Databricks Workspaces](https://www.databricks.com/blog/2022/03/10/functional-workspace-organization-on-databricks.html)

---

## 6. Provisioning for 40-50 Participants

### Option 1: Free Edition (Decentralized)

**Pros:**
- Zero cost
- No administrative overhead for provisioning
- Each participant has their own isolated environment
- Good for learning-focused workshops

**Cons:**
- No centralized monitoring or control
- Participants must self-register
- Daily quota limits may affect intensive workshops
- No Scala/R/RDD support

**Implementation Steps:**
1. Create workshop materials in Python/SQL only
2. Upload workshop datasets to Databricks Marketplace
3. Send registration instructions to all participants
4. Provide notebook import instructions
5. Have backup plan for quota-exceeded scenarios

### Option 2: 14-Day Trial (Decentralized with Full Features)

**Pros:**
- Full Databricks features
- $400 credits per participant
- All languages supported

**Cons:**
- Participants may need payment information
- 14-day time limit
- No centralized control

### Option 3: Enterprise/Partner Workshop (Centralized)

**Pros:**
- Full administrative control
- Centralized user management
- Pre-provisioned environments
- Progress monitoring
- Custom cluster policies

**Cons:**
- Requires partnership or commercial arrangement
- Potential costs involved
- More complex setup

**Implementation Steps:**
1. Contact Databricks sales/partnerships or use CloudLabs
2. Set up enterprise workspace
3. Configure Identity Provider groups
4. Create cluster policies with resource limits
5. Pre-load datasets to Unity Catalog
6. Provision user accounts via SCIM or manual import
7. Set up monitoring dashboards

### Recommended Approach for 40-50 Participants

| Workshop Type | Recommended Option |
|---------------|-------------------|
| **University/Education** | Free Edition (individual accounts) |
| **Corporate Training** | 14-Day Trial or Enterprise Setup |
| **Partner/Customer Workshop** | CloudLabs or Databricks Partnership |
| **Conference Demo** | Free Edition (demo account) |
| **Multi-day Bootcamp** | Enterprise Setup with CloudLabs |

---

## 7. Sample Datasets Available in Databricks

### Unity Catalog Sample Datasets (Recommended)

All Free Edition and Trial accounts have access to the `samples` catalog in Unity Catalog:

```sql
-- Access pattern: samples.<schema>.<table>
SELECT * FROM samples.nyctaxi.trips LIMIT 10;
```

#### Available Schemas and Tables

| Catalog | Schema | Tables | Description |
|---------|--------|--------|-------------|
| samples | nyctaxi | trips | NYC taxi ride data (pickup/dropoff, fares, tips) |
| samples | tpch | Multiple tables | TPC-H benchmark data (orders, customers, suppliers) |
| samples | tpcds_sf1 | Multiple tables | TPC-DS benchmark data (web sales, inventory, stores) |

#### Listing Available Tables
```sql
-- List all tables in nyctaxi schema
SHOW TABLES IN samples.nyctaxi;

-- List all tables in TPC-H schema
SHOW TABLES IN samples.tpch;

-- List all tables in TPC-DS schema
SHOW TABLES IN samples.tpcds_sf1;
```

### Additional Dataset Sources

1. **Third-Party CSV Datasets:**
   - NYC Squirrel Census
   - Our World in Data (OWID)
   - Data.gov datasets
   - Kaggle datasets

2. **Python Package Datasets:**
   - scikit-learn: `sklearn.datasets`
   - seaborn: `seaborn.load_dataset()`
   - Hugging Face: `datasets` library

3. **Legacy DBFS Datasets** (Not recommended for Unity Catalog-enabled workspaces):
   - Located at `/databricks-datasets/`
   - Browse with: `dbutils.fs.ls("/databricks-datasets/")`

### Workshop Dataset Recommendations

| Workshop Topic | Recommended Dataset |
|----------------|---------------------|
| SQL Basics | samples.nyctaxi.trips |
| Data Engineering | samples.tpch (multiple tables for joins) |
| Performance Testing | samples.tpcds_sf1 |
| Machine Learning | scikit-learn built-in datasets |
| Streaming (simulated) | Convert nyctaxi to streaming source |

**Sources:**
- [Databricks Sample Datasets (AWS)](https://docs.databricks.com/aws/en/discover/databricks-datasets)
- [Databricks Sample Datasets (Azure)](https://learn.microsoft.com/en-us/azure/databricks/discover/databricks-datasets)

---

## 8. Unity Catalog Access in Free/Trial Tiers

### Unity Catalog in Free Edition

**Good news:** Unity Catalog is included in Free Edition at no additional cost.

Features available:
- Centralized data catalog
- Access control
- Data lineage
- Quality monitoring
- Data discovery
- Three-level namespace (catalog.schema.table)

Limitations:
- One metastore per account
- One workspace per account
- No account-level administration
- Cannot create external locations (cloud storage mounts)

### Unity Catalog in 14-Day Trial

Full Unity Catalog capabilities:
- Multiple workspaces
- Multiple metastores
- External locations
- Full admin console
- Complete governance features

### Unity Catalog in Paid Tiers

Unity Catalog features are included at no additional charge with Premium or Enterprise tiers.

**Note:** Accounts created after November 8, 2023 have Unity Catalog enabled by default.

**Sources:**
- [Unity Catalog Overview](https://www.databricks.com/product/unity-catalog)
- [What is Unity Catalog (Azure)](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/)

---

## 9. Time Limits and Compute Restrictions Summary

### Free Edition Quotas

| Resource | Limit |
|----------|-------|
| Daily compute usage | Subject to "fair usage policy" |
| Concurrent job tasks | 5 maximum |
| SQL warehouses | 1 (2X-Small max) |
| All-purpose clusters | 1 (small, CPU-only) |
| Vector search endpoints | 1 (1 unit) |
| DLT pipelines | 1 per type |
| Databricks Apps | 1 (auto-stops after 24 hours) |
| Workspaces | 1 per account |

**What happens when quota is exceeded:**
- Compute resources shut down for remainder of the day
- In extreme cases, shutdown extends through the month
- Data and settings are preserved
- Access resumes when quota resets (next day)

**Note:** Databricks states that "99% or more of users will not experience rate limitations or throttling" under normal use.

### 14-Day Trial Limits

| Resource | Limit |
|----------|-------|
| Duration | 14 days |
| Credits | $400 worth of DBUs |
| Compute (personal email) | 50 DBUs/hour max |
| SQL warehouse (personal email) | 50 DBUs/hour max, 1 per workspace |
| GPUs (personal email) | Not available |

Trial ends when:
- 14 days elapse, OR
- $400 credits exhausted

### DBU Consumption Reference

Approximate DBU costs (varies by cloud and region):
- Interactive notebooks: ~4x more expensive than automated jobs
- Basic compute: $0.07-0.15/DBU
- Premium features: $0.22-0.65/DBU
- Real-time jobs: Higher DBU rates

**Tip for workshops:** Use automated jobs where possible instead of interactive notebooks to maximize credit usage.

**Sources:**
- [Resource Limits (AWS)](https://docs.databricks.com/aws/en/resources/limits)
- [Serverless Compute Quotas (Azure)](https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/serverless-quotas)
- [Free Edition FAQ](https://community.databricks.com/t5/databricks-university-alliance/free-edition-frequently-asked-questions-faqs-consolitated/ta-p/128500)

---

## 10. Workshop Checklist

### Pre-Workshop Preparation (1-2 Weeks Before)

- [ ] Decide on Free Edition vs Trial vs Enterprise setup
- [ ] Prepare all materials in supported languages (Python/SQL for Free Edition)
- [ ] Test materials in target environment
- [ ] Create Marketplace listing for datasets (optional)
- [ ] Prepare GitHub repository with notebooks
- [ ] Send registration instructions to participants
- [ ] Create backup plan for quota/credit issues

### Day Before Workshop

- [ ] Verify all participants have registered
- [ ] Test sample dataset access
- [ ] Prepare troubleshooting guide
- [ ] Set up communication channel (Slack/Teams/email)

### Workshop Day

- [ ] Have participants verify account access
- [ ] Walk through notebook import process
- [ ] Monitor for quota issues
- [ ] Provide alternative exercises if compute unavailable
- [ ] Document common issues for future workshops

### Post-Workshop

- [ ] Collect feedback on environment
- [ ] Document lessons learned
- [ ] Update materials based on experience
- [ ] Clean up any temporary resources

---

## 11. Contact and Support Resources

| Purpose | Contact/Resource |
|---------|------------------|
| Free Edition Help | free_edition_help@databricks.com |
| University Alliance | [Databricks University Alliance](https://www.databricks.com/university) |
| Training Catalog | [Databricks Training](https://www.databricks.com/training/catalog) |
| Community Forums | [Databricks Community](https://community.databricks.com/) |
| Documentation (AWS) | [docs.databricks.com](https://docs.databricks.com/aws/en/) |
| Documentation (Azure) | [learn.microsoft.com/azure/databricks](https://learn.microsoft.com/en-us/azure/databricks/) |
| CloudLabs (Lab Platform) | [cloudlabs.ai](https://cloudlabs.ai/) |

---

## Appendix: Quick Reference Commands

### Unity Catalog Sample Data Access
```sql
-- NYC Taxi Data
SELECT * FROM samples.nyctaxi.trips LIMIT 100;

-- TPC-H Data
SELECT * FROM samples.tpch.customer LIMIT 100;
SELECT * FROM samples.tpch.orders LIMIT 100;

-- List available schemas
SHOW SCHEMAS IN samples;

-- List tables in a schema
SHOW TABLES IN samples.nyctaxi;
```

### Python Notebook Setup
```python
# Read sample data as DataFrame
df = spark.table("samples.nyctaxi.trips")
df.display()

# Check available tables
spark.sql("SHOW TABLES IN samples.nyctaxi").display()
```

### Import External Datasets
```python
# From URL (CSV)
df = spark.read.csv("https://example.com/data.csv", header=True, inferSchema=True)

# From Python package
from sklearn import datasets
iris = datasets.load_iris()
```

---

**Document Version:** 1.0
**Last Updated:** January 26, 2026
**Research Confidence:** High (based on official documentation and community sources)
