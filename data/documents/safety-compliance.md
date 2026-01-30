# Velocity Motors — Safety & Compliance Procedures

This document defines the safety feature standards, VIN structure and decoding procedures, recall handling protocols, pre-delivery inspection requirements, and NHTSA compliance obligations for all Velocity Motors dealership operations. For warranty implications of safety-related repairs, see [Vehicle Warranty Policy](vehicle-warranty-policy.md). For recall service scheduling and costing, see [Service & Maintenance Policy](service-maintenance-policy.md).

## Safety Features

Velocity Motors sells vehicles equipped with **8 primary safety features**. Feature availability varies by make, model, and trim level. All safety features are inspected during pre-delivery and CPO certification processes.

### Safety Feature Inventory

| # | Feature | Description |
|---|---|---|
| 1 | **Blind Spot Monitor** | Alerts the driver to vehicles in adjacent lanes via side-mirror indicators and/or audible warnings |
| 2 | **Lane Departure Warning** | Monitors lane markings and alerts the driver when the vehicle drifts without a turn signal activated |
| 3 | **Forward Collision Warning** | Uses radar or camera sensors to detect an imminent frontal collision and alerts the driver |
| 4 | **Automatic Emergency Braking** | Automatically applies brakes when a collision is imminent and the driver has not responded to warnings |
| 5 | **Adaptive Cruise Control** | Maintains a set speed while automatically adjusting to maintain a safe following distance |
| 6 | **360 Camera** | Provides a bird's-eye composite view around the vehicle using multiple exterior cameras |
| 7 | **Rear Cross Traffic Alert** | Detects vehicles approaching from the sides when reversing out of a parking space |
| 8 | **Parking Sensors** | Ultrasonic sensors in front and/or rear bumpers that provide audible proximity alerts |

### Feature Distribution by Trim Level

Safety feature availability follows a tiered distribution based on vehicle trim level:

| Trim Category | Feature Count | Share of Inventory | Typical Equipment |
|---|---|---|---|
| **Premium / Luxury Trims** | 6 - 10 features | ~40% of inventory | All 8 standard features plus make-specific advanced systems (e.g., BMW Night Vision, Mercedes Pre-Safe) |
| **Standard Trims** | 3 - 7 features | ~60% of inventory | Typically includes Forward Collision Warning, Automatic Emergency Braking, Blind Spot Monitor, and Rear Cross Traffic Alert as standard; other features optional |

Approximately **60% of all safety features across inventory are standard** (included at no additional cost), while **40% are optional** (available as part of packages or individual options).

### Safety Feature Availability by Make

| Make | Standard Features (Typical) | Optional Features (Typical) | MSRP Range |
|---|---|---|---|
| **Ford** | Forward Collision Warning, Automatic Emergency Braking, Blind Spot Monitor | Adaptive Cruise Control, 360 Camera, Lane Departure Warning | $28,000 - $85,000 |
| **Toyota** | Forward Collision Warning, Automatic Emergency Braking, Lane Departure Warning, Adaptive Cruise Control | 360 Camera, Blind Spot Monitor, Rear Cross Traffic Alert | $22,000 - $70,000 |
| **Honda** | Forward Collision Warning, Automatic Emergency Braking, Lane Departure Warning | Blind Spot Monitor, Adaptive Cruise Control, Parking Sensors | $24,000 - $55,000 |
| **Chevrolet** | Forward Collision Warning, Automatic Emergency Braking | Blind Spot Monitor, Lane Departure Warning, Adaptive Cruise Control, 360 Camera | $26,000 - $90,000 |
| **BMW** | All 8 features standard on most trims | Night Vision, Head-Up Display, Parking Assistant Plus | $45,000 - $150,000 |
| **Mercedes-Benz** | All 8 features standard on most trims | Pre-Safe, Active Steering Assist, Evasive Steering Assist | $48,000 - $180,000 |

## VIN Structure and Decoding

Every vehicle sold by Velocity Motors is identified by a **17-character Vehicle Identification Number (VIN)**. The VIN is a critical compliance tool used for title registration, warranty tracking, recall identification, and regulatory reporting.

### VIN Position Breakdown

| Position | Name | Content |
|---|---|---|
| **1 - 3** | World Manufacturer Identifier (WMI) | Identifies the manufacturer and country of origin |
| **4 - 8** | Vehicle Descriptor Section (VDS) | Encodes vehicle attributes: model, body type, engine, transmission, restraint system |
| **9** | Check Digit | Mathematical check digit for VIN validation |
| **10** | Model Year | Single character encoding the model year (e.g., R = 2024, S = 2025) |
| **11 - 17** | Vehicle Identifier Section (VIS) | Plant code (position 11) and sequential production serial number (positions 12-17) |

### Velocity Motors WMI Codes

The following WMI codes identify the **6 primary makes** sold by Velocity Motors:

| WMI Code | Make | Country of Origin |
|---|---|---|
| **1FA** | Ford | United States |
| **2T1** | Toyota | Canada |
| **1HG** | Honda | United States |
| **3GN** | Chevrolet | Mexico |
| **WBA** | BMW | Germany |
| **WDD** | Mercedes-Benz | Germany |

### VIN Validation Rules

All VINs must pass the following validation checks before a vehicle is entered into inventory:

1. **Length Check**: VIN must be exactly 17 characters
2. **Character Validation**: Only alphanumeric characters; letters I, O, and Q are prohibited (to avoid confusion with 1, 0, and 9)
3. **Check Digit Verification**: Position 9 must contain the correct check digit calculated using the NHTSA-specified algorithm (weighted sum modulo 11)
4. **WMI Verification**: Positions 1-3 must match a known manufacturer code from the NHTSA database
5. **Model Year Verification**: Position 10 must encode a valid model year consistent with the vehicle's physical characteristics

VIN decoding is performed automatically by the dealership management system at the time of inventory intake. Any VIN that fails validation is flagged for manual review before the vehicle can be listed for sale.

## Recall Handling Procedures

Velocity Motors follows strict protocols for identifying and resolving open safety recalls on all vehicles in inventory and on customer-owned vehicles serviced at our facilities.

### Pre-Sale Recall Requirements

**Open recalls must be resolved before customer delivery.** No vehicle — New, CPO, or Used — may be delivered to a customer with an open safety recall. This requirement applies to:

- All new inventory received from manufacturers
- All trade-in vehicles accepted for resale
- All auction purchases
- All CPO certification candidates

### Recall Identification Process

1. **Inventory Intake**: Every vehicle entering inventory is checked against the NHTSA recall database using the VIN at the time of intake.
2. **Daily Scan**: The dealership management system performs a nightly batch scan of all inventory VINs against the NHTSA database to identify newly issued recalls.
3. **Service Visit Check**: Every vehicle presented for service (regardless of the reason for the visit) is scanned for open recalls. If an open recall is found, the service advisor informs the customer and offers to perform the recall service during the same visit.

### Recall Service Terms

| Parameter | Value |
|---|---|
| **Cost to Customer** | $0 (always free) |
| **Service Duration** | 60 - 240 minutes (varies by recall complexity) |
| **Parts Source** | Manufacturer-supplied recall parts only |
| **Labor Reimbursement** | Manufacturer reimburses dealer at agreed labor rate |
| **Documentation** | Recall completion logged in NHTSA database and dealership management system |
| **Service Volume Share** | 2% of total service orders |

Recall services are performed according to the manufacturer's Technical Service Bulletin (TSB) for the specific recall campaign. Technicians must complete manufacturer-required training before performing recall repairs. See [Service & Maintenance Policy](service-maintenance-policy.md) for full recall service pricing and scheduling details.

### Customer Notification

When a new recall is issued affecting a vehicle previously sold by Velocity Motors:

1. **Manufacturer Notification**: The manufacturer sends recall notices to registered owners via mail.
2. **Dealership Follow-Up**: Velocity Motors sends a supplemental notification via email and/or phone within 7 days of recall announcement to all affected owners in the customer database.
3. **Scheduling**: Customers are offered priority scheduling for recall service. Fleet customers (SEG-002) receive same-day or next-business-day recall service.

## NHTSA Compliance

Velocity Motors maintains compliance with all **National Highway Traffic Safety Administration (NHTSA)** regulations, including but not limited to:

### Regulatory Requirements

- **Safety Standard Compliance**: All vehicles sold must meet applicable Federal Motor Vehicle Safety Standards (FMVSS)
- **Recall Compliance**: 100% of open recalls must be resolved before retail delivery
- **Reporting Obligations**: Early Warning Reporting (EWR) data submitted as required for warranty claims, field reports, and consumer complaints
- **Monroney Label**: All New vehicles must display the manufacturer's window sticker (Monroney label) with MSRP, equipment, fuel economy, and safety ratings until the time of sale
- **Buyer's Guide**: All Used vehicles must display the FTC Buyer's Guide with warranty terms (as-is or limited warranty) in a conspicuous location on the vehicle

### Compliance Audits

Velocity Motors conducts compliance audits on the following schedule:

| Audit Type | Frequency | Scope |
|---|---|---|
| Recall Compliance | Monthly | 100% of inventory VINs checked against NHTSA database |
| Safety Feature Verification | Per Vehicle | Pre-delivery inspection confirms all advertised safety features are functional |
| Documentation Review | Quarterly | Title, registration, warranty, and disclosure records audited |
| Technician Certification | Annually | All technicians verified current on manufacturer training and ASE certifications |

## Pre-Delivery Inspection

Every vehicle delivered to a customer — regardless of condition category (New, CPO, or Used) — must pass a **Pre-Delivery Inspection (PDI)** performed by a certified technician.

### PDI Checklist Summary

| Category | Items Verified |
|---|---|
| **Exterior** | Paint condition, body panel alignment, glass integrity, lighting function, tire condition and pressure |
| **Interior** | Seat function, climate control, infotainment system, all switches and controls, odor check |
| **Safety Systems** | All installed safety features operational (Blind Spot Monitor, Lane Departure Warning, Forward Collision Warning, Automatic Emergency Braking, Adaptive Cruise Control, 360 Camera, Rear Cross Traffic Alert, Parking Sensors) |
| **Mechanical** | Engine start and idle, transmission shifting, brake function, steering alignment, suspension |
| **Fluids** | Engine oil, coolant, brake fluid, transmission fluid, power steering fluid, washer fluid — all at proper levels |
| **Electrical** | Battery voltage, charging system, all exterior and interior lighting, horn, power windows, power locks |
| **Documentation** | VIN matches all documents, open recalls resolved, warranty registration complete, owner's manual and spare key present |

### PDI Sign-Off

The PDI must be signed by the performing technician and reviewed by the service manager before the vehicle is cleared for delivery. A copy of the completed PDI checklist is retained in the vehicle's service file and a summary is provided to the customer at delivery.

## Vehicle Makes and MSRP Summary

The following table consolidates all **6 primary makes** sold by Velocity Motors with their MSRP ranges and identification codes:

| Make | MSRP Range | VIN WMI Code | Premium Trim Safety Features | Standard Trim Safety Features |
|---|---|---|---|---|
| **Ford** | $28,000 - $85,000 | 1FA | 6 - 8 | 3 - 5 |
| **Toyota** | $22,000 - $70,000 | 2T1 | 7 - 8 | 4 - 6 |
| **Honda** | $24,000 - $55,000 | 1HG | 6 - 8 | 3 - 5 |
| **Chevrolet** | $26,000 - $90,000 | 3GN | 6 - 8 | 2 - 4 |
| **BMW** | $45,000 - $150,000 | WBA | 8 - 10 | 6 - 7 |
| **Mercedes-Benz** | $48,000 - $180,000 | WDD | 8 - 10 | 6 - 7 |

For warranty coverage by make, see [Vehicle Warranty Policy](vehicle-warranty-policy.md). For make-specific service pricing considerations, see [Service & Maintenance Policy](service-maintenance-policy.md).

## Incident Reporting

Any safety-related incident involving a Velocity Motors vehicle (whether in inventory or customer-owned during service) must be reported:

### Reporting Protocol

1. **Immediate**: Secure the scene and ensure all persons are safe. Contact emergency services if needed.
2. **Within 1 Hour**: Notify the General Manager and document the incident with photographs, witness statements, and vehicle identification (VIN).
3. **Within 24 Hours**: Complete the Velocity Motors Incident Report Form and submit to the regional compliance officer.
4. **Within 5 Business Days**: If the incident involves a potential safety defect, file a Vehicle Owner Questionnaire (VOQ) with NHTSA at safercar.gov.

### Record Retention

All safety and compliance records are retained for a minimum of **10 years** or the useful life of the vehicle, whichever is longer. Electronic records are backed up daily. Physical records are stored in fireproof filing systems.

Effective Date: January 2026
