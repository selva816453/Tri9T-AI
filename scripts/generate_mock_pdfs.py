"""
Generate mock CT-200 Blood Pressure Monitor Manual PDFs (v1 and v2).
Includes intentional structural variations to test the parser:
  - Duplicate headings with different content
  - Inconsistent heading levels
  - Tables
  - Multi-level lists
  - Figures with captions
  - Sections with long body text and sub-subsections
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, ListFlowable, ListItem,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import os

PAGE_W, PAGE_H = A4

# ─── style helpers ────────────────────────────────────────────────────────────

def make_styles():
    base = getSampleStyleSheet()

    def add(name, parent="Normal", **kw):
        base.add(ParagraphStyle(name=name, parent=base[parent], **kw))

    add("DocTitle", parent="Title", fontSize=22, spaceAfter=10, alignment=TA_CENTER, textColor=colors.HexColor("#1a1a2e"))
    add("DocSubtitle", fontSize=14, spaceAfter=6, alignment=TA_CENTER, textColor=colors.HexColor("#16213e"))
    add("H1", parent="Heading1", fontSize=16, spaceBefore=18, spaceAfter=8, textColor=colors.HexColor("#0f3460"))
    add("H2", parent="Heading2", fontSize=13, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#533483"))
    add("H3", parent="Heading3", fontSize=11, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#e94560"))
    add("Body", parent="Normal", fontSize=10, leading=15, spaceAfter=6, alignment=TA_JUSTIFY)
    add("Note", parent="Normal", fontSize=9, leading=13, textColor=colors.HexColor("#444444"), leftIndent=20)
    add("FigCaption", parent="Normal", fontSize=9, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=8)
    add("Warning", parent="Normal", fontSize=10, backColor=colors.HexColor("#fff3cd"),
        borderColor=colors.HexColor("#ffc107"), borderWidth=1, borderPadding=6, spaceAfter=8)
    add("TableHeader", parent="Normal", fontSize=10, textColor=colors.white,
        backColor=colors.HexColor("#0f3460"), alignment=TA_CENTER)
    add("BulletBody", parent="Normal", fontSize=10, leading=14)
    return base

S = make_styles()

def h1(t):  return Paragraph(t, S["H1"])
def h2(t):  return Paragraph(t, S["H2"])
def h3(t):  return Paragraph(t, S["H3"])
def body(t): return Paragraph(t, S["Body"])
def note(t): return Paragraph(f"<i>Note: {t}</i>", S["Note"])
def warn(t): return Paragraph(f"⚠ WARNING: {t}", S["Warning"])
def cap(t):  return Paragraph(t, S["FigCaption"])
def sp(h=8): return Spacer(1, h)
def hr():    return HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4)

# ─── v1 content ───────────────────────────────────────────────────────────────

def v1_content():
    els = []

    # Cover
    els += [
        sp(60),
        Paragraph("CardioTrack CT-200", S["DocTitle"]),
        Paragraph("Home Blood Pressure Monitor", S["DocSubtitle"]),
        Paragraph("User Manual &amp; Technical Reference", S["DocSubtitle"]),
        sp(4),
        Paragraph("Version 1.0 | Document ID: CT200-MAN-001", S["DocSubtitle"]),
        Paragraph("Tri9T Medical Devices Inc. | Confidential", S["DocSubtitle"]),
        PageBreak(),
    ]

    # Table of Contents (plain text, not auto-linked — parser edge case)
    els += [
        h1("Table of Contents"),
        body("1. Introduction and Intended Use ............................... 3"),
        body("2. Safety Warnings and Precautions ............................. 4"),
        body("3. Device Description and Components ........................... 6"),
        body("4. Installation and Setup ...................................... 8"),
        body("5. Operating Instructions ...................................... 10"),
        body("6. Measurement Accuracy and Clinical Validation ................ 13"),
        body("7. Maintenance and Troubleshooting ............................. 15"),
        body("8. Error Codes ................................................. 17"),
        body("9. Technical Specifications .................................... 19"),
        body("10. Regulatory and Compliance Information ...................... 21"),
        body("Appendix A: Glossary ........................................... 23"),
        PageBreak(),
    ]

    # Section 1 – Introduction
    els += [
        h1("1. Introduction and Intended Use"),
        hr(),
        body("The CardioTrack CT-200 is a non-invasive automated oscillometric blood pressure monitor "
             "intended for home use by adult patients under the supervision of a healthcare professional. "
             "It measures systolic and diastolic blood pressure and pulse rate using the oscillometric method."),
        body("This device is intended for use on the upper arm of adults aged 18 years and older. "
             "It is not intended to replace clinical-grade sphygmomanometers used by trained medical staff."),

        h2("1.1 Indications for Use"),
        body("The CT-200 is indicated for use in the following clinical contexts:"),
        ListFlowable([
            ListItem(Paragraph("Home blood pressure monitoring for hypertensive patients.", S["BulletBody"])),
            ListItem(Paragraph("Ambulatory blood pressure tracking as part of a physician-prescribed regimen.", S["BulletBody"])),
            ListItem(Paragraph("Wellness monitoring for individuals at risk of cardiovascular disease.", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),

        h2("1.2 Contraindications"),
        body("Do not use the CT-200 in the following situations:"),
        ListFlowable([
            ListItem(Paragraph("Patients with cardiac arrhythmias, as irregular pulse may affect measurement accuracy.", S["BulletBody"])),
            ListItem(Paragraph("Patients with arteriovenous fistula or dialysis shunts in the measurement arm.", S["BulletBody"])),
            ListItem(Paragraph("During infusion or IV administration in the measurement arm.", S["BulletBody"])),
            ListItem(Paragraph("Patients with Raynaud's disease or other severe circulation disorders.", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),

        h2("1.3 Patient Population"),
        body("This device is validated for adult patients with an upper arm circumference between 22 cm and 42 cm. "
             "A separate paediatric cuff is available but is out of scope for this manual. "
             "Do not use on neonates or infants."),
        note("The CT-200 has NOT been validated for use during pregnancy or in patients with pre-eclampsia. "
             "Clinical judgement should be exercised."),
        PageBreak(),
    ]

    # Section 2 – Safety Warnings
    els += [
        h1("2. Safety Warnings and Precautions"),
        hr(),
        warn("Do not use near high-frequency surgical equipment, MRI machines, or defibrillators. "
             "Electromagnetic interference may cause inaccurate readings or device malfunction."),
        warn("Do not attempt to disassemble, modify, or repair the device. Unauthorized modification "
             "voids the warranty and may create electrical or mechanical hazards."),

        h2("2.1 Electrical Safety"),
        body("The CT-200 operates on 4 × AA alkaline batteries (IEC LR6) or via the included AC adapter (100–240 V AC, 50/60 Hz). "
             "Never use both power sources simultaneously. Disconnect the AC adapter before replacing batteries."),
        body("The device complies with IEC 60601-1 requirements for electrical safety in medical equipment. "
             "The enclosure is rated IP21 (drip-proof) but is not waterproof. Do not immerse in liquids."),

        h2("2.2 Cuff Pressure Safety"),
        body("The device automatically deflates if cuff pressure exceeds 300 mmHg. "
             "If over-pressurisation occurs during a measurement, the device will display error code E3 "
             "and auto-deflate within 2 seconds. Continuous re-inflation attempts without a rest period "
             "of at least 2 minutes may cause discomfort or circulatory impairment."),

        h2("2.3 Electromagnetic Compatibility"),
        body("The CT-200 has been tested for EMC compliance in accordance with IEC 60601-1-2 (4th edition). "
             "The device is classified as Equipment Class B, suitable for use in home and hospital environments. "
             "Portable RF communications equipment (e.g., mobile phones) should be kept at least 30 cm from the device during measurements."),

        h2("2.4 Disposal and Environmental Considerations"),
        body("Do not dispose of this device with household waste. Dispose of batteries in accordance "
             "with local regulations. The device contains recyclable materials; contact Tri9T Medical "
             "Devices for return and recycling instructions."),
        PageBreak(),
    ]

    # Section 3 – Device Description
    els += [
        h1("3. Device Description and Components"),
        hr(),
        body("The CT-200 system consists of the following components:"),

        h2("3.1 Main Unit"),
        body("The main unit houses the measurement electronics, display, and control interface. "
             "Dimensions: 135 mm × 95 mm × 55 mm. Weight (without batteries): 280 g."),
        body("The front panel includes:"),
        ListFlowable([
            ListItem(Paragraph("3.5-inch LCD display (128×64 pixels) with backlight.", S["BulletBody"])),
            ListItem(Paragraph("START/STOP button (large, tactile, blue).", S["BulletBody"])),
            ListItem(Paragraph("MEMORY button for reviewing stored readings.", S["BulletBody"])),
            ListItem(Paragraph("CLOCK SET button for date/time configuration.", S["BulletBody"])),
            ListItem(Paragraph("Power indicator LED (green: on; red: low battery).", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        cap("Figure 3-1: Front panel layout of the CT-200 main unit. See Appendix B for detailed diagram."),

        h2("3.2 Cuff and Tubing"),
        body("The standard cuff (model CT200-CF-M) fits upper arms 22–42 cm in circumference. "
             "The cuff is constructed from washable nylon fabric with a latex-free internal bladder. "
             "The air tube length is 60 cm with a standard Luer-type connector."),
        note("Replacement cuffs must be sourced from Tri9T Medical Devices or an authorised distributor. "
             "Third-party cuffs may affect measurement accuracy and void the warranty."),

        h2("3.3 Connectivity"),
        body("The CT-200 includes a micro-USB port for data export to a PC via the CardioLink software (Windows 10/11, macOS 12+). "
             "Bluetooth 5.0 LE is available for wireless data transfer to the CardioTrack mobile application "
             "(iOS 14+ / Android 9+). Data is transmitted using the Bluetooth Health Device Profile (HDP)."),

        h2("3.4 Memory and Data Storage"),
        body("The device stores up to 120 readings (60 per user slot in a 2-user configuration). "
             "Each reading includes: date, time, systolic BP, diastolic BP, pulse rate, and an irregular heartbeat (IHB) indicator. "
             "Memory is retained when batteries are replaced, provided replacement is completed within 60 seconds."),

        # INTENTIONAL EDGE CASE: duplicate heading "3.4 Memory and Data Storage" used again at a lower heading level
        h3("3.4.1 Data Security and Privacy"),
        body("No patient-identifiable information is stored on the device. "
             "All data exported via USB or Bluetooth is in raw measurement format (not encrypted by the device). "
             "Healthcare providers should apply appropriate data-handling policies when transferring readings."),
        PageBreak(),
    ]

    # Section 4 – Installation
    els += [
        h1("4. Installation and Setup"),
        hr(),

        h2("4.1 Battery Installation"),
        body("Open the battery compartment on the bottom of the main unit by sliding the cover in the direction "
             "indicated by the arrow. Insert 4 × AA batteries observing correct polarity (marked inside the compartment). "
             "Replace the cover until it clicks into place."),
        warn("Use only fresh alkaline batteries. Do not mix old and new batteries or batteries of different types. "
             "Remove batteries if the device will not be used for more than 3 months."),

        h2("4.2 AC Adapter Connection"),
        body("Connect the AC adapter to the DC IN port on the right side of the main unit, then plug the adapter "
             "into a standard AC outlet. The power LED will illuminate green. The battery icon on the display will "
             "be replaced by a plug icon when AC power is active."),

        h2("4.3 Date and Time Setup"),
        body("On first use, the display will show the time setup screen. Use the CLOCK SET button to enter setup mode, "
             "then use START/STOP to cycle through digits and MEMORY to confirm each field. "
             "Fields: Year → Month → Day → Hour → Minute. Press CLOCK SET again to exit."),

        h2("4.4 Cuff Fitting"),
        body("Proper cuff placement is critical for accurate readings. Follow these steps:"),
        ListFlowable([
            ListItem(Paragraph("Rest for 5 minutes before measuring. Avoid caffeine, smoking, or strenuous exercise for 30 minutes prior.", S["BulletBody"])),
            ListItem(Paragraph("Sit in a chair with back supported. Keep feet flat on the floor.", S["BulletBody"])),
            ListItem(Paragraph("Place the left arm on a flat surface at heart level. Palm facing upward.", S["BulletBody"])),
            ListItem(Paragraph("Wrap the cuff around the upper arm, 2–3 cm above the elbow. The artery marker (▷) should align with the brachial artery.", S["BulletBody"])),
            ListItem(Paragraph("Ensure the cuff is snug but not tight — you should be able to slide two fingers under it.", S["BulletBody"])),
            ListItem(Paragraph("Connect the air tube to the main unit.", S["BulletBody"])),
        ], bulletType='1', leftIndent=30),
        sp(),
        cap("Figure 4-1: Correct cuff placement on the upper left arm."),
        PageBreak(),
    ]

    # Section 5 – Operating Instructions
    els += [
        h1("5. Operating Instructions"),
        hr(),

        h2("5.1 Taking a Measurement"),
        body("Once the device is set up (see Section 4), press the START/STOP button to begin a measurement. "
             "The cuff will automatically inflate. Remain still and do not talk during inflation and measurement. "
             "After approximately 30–60 seconds, the cuff will deflate and the reading will be displayed."),
        body("The display shows: systolic (top), diastolic (bottom), and pulse rate (right). "
             "A WHO risk indicator (colour bar) is shown if the optional display mode is enabled."),

        h2("5.2 Reading the Results"),
        body("Blood pressure categories per WHO/ESH 2023 guidelines:"),

        Table(
            [
                [Paragraph("Category", S["TableHeader"]),
                 Paragraph("Systolic (mmHg)", S["TableHeader"]),
                 Paragraph("Diastolic (mmHg)", S["TableHeader"])],
                ["Optimal",         "< 120",    "< 80"],
                ["Normal",          "120–129",  "80–84"],
                ["High Normal",     "130–139",  "85–89"],
                ["Grade 1 HT",      "140–159",  "90–99"],
                ["Grade 2 HT",      "160–179",  "100–109"],
                ["Grade 3 HT",      "≥ 180",    "≥ 110"],
            ],
            colWidths=[2.4*inch, 2.0*inch, 2.0*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        sp(10),

        h2("5.3 Irregular Heartbeat Detection"),
        body("If the device detects an irregular heartbeat pattern during measurement, the IHB symbol (♥?) "
             "will appear on the display. This is an indication only — it does not constitute a clinical diagnosis. "
             "Consult a healthcare provider if this symbol appears frequently."),

        h2("5.4 Memory Recall"),
        body("Press the MEMORY button to display stored readings. The display will show the reading number, "
             "date/time, and measurement values. Readings are stored in chronological order, with the most recent first. "
             "To scroll through readings, press MEMORY repeatedly. Press START/STOP to return to normal mode."),

        h2("5.5 Multi-User Mode"),
        body("The CT-200 supports two user profiles (User 1 and User 2). "
             "To switch users, hold the MEMORY button for 3 seconds. "
             "Each user has an independent 60-reading memory. "
             "User profiles do not store personal identifiers — they are simply two separate memory banks."),

        # EDGE CASE: heading skips a level (H2 directly contains H3 without an intermediate sub-section)
        h3("5.5.1 Switching Users During a Measurement"),
        body("Do not attempt to switch user profiles during an active measurement. "
             "If the MEMORY button is held during cuff inflation or measurement, the action will be ignored "
             "and the measurement will continue unaffected."),
        PageBreak(),
    ]

    # Section 6 – Accuracy
    els += [
        h1("6. Measurement Accuracy and Clinical Validation"),
        hr(),

        h2("6.1 Accuracy Specifications"),
        body("The CT-200 has been validated in accordance with ISO 81060-2:2018 (Non-invasive sphygmomanometers — "
             "Clinical validation of automated measurement type). The following accuracy specifications apply:"),
        Table(
            [
                [Paragraph("Parameter", S["TableHeader"]),
                 Paragraph("Specification", S["TableHeader"]),
                 Paragraph("Standard", S["TableHeader"])],
                ["Blood Pressure (BP)",   "±3 mmHg or 2% of reading", "ISO 81060-2"],
                ["Pulse Rate",            "±5% of reading",           "ISO 81060-2"],
                ["Cuff Pressure Range",   "0–300 mmHg",               "IEC 60601-2-30"],
                ["Static Pressure Acc.",  "±3 mmHg",                  "IEC 60601-2-30"],
            ],
            colWidths=[2.4*inch, 2.3*inch, 1.7*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        sp(10),

        h2("6.2 Clinical Study Results"),
        body("A clinical validation study was conducted at St. Michael's Cardiovascular Institute (n=85 subjects, "
             "age range 21–78, BMI 18.5–35.2 kg/m²) under the supervision of a registered cardiologist. "
             "The study protocol was reviewed and approved by the institutional ethics board."),
        body("Study outcomes (per ISO 81060-2 grading criteria):"),
        ListFlowable([
            ListItem(Paragraph("Mean difference (device vs. reference): −0.8 mmHg systolic, +1.1 mmHg diastolic.", S["BulletBody"])),
            ListItem(Paragraph("Standard deviation of differences: 3.7 mmHg systolic, 3.4 mmHg diastolic.", S["BulletBody"])),
            ListItem(Paragraph("Grade A classification achieved for both systolic and diastolic measurements.", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),

        h2("6.3 Factors Affecting Accuracy"),
        body("The following factors may affect measurement accuracy and should be considered when interpreting results:"),
        ListFlowable([
            ListItem(Paragraph("Body movement or talking during measurement.", S["BulletBody"])),
            ListItem(Paragraph("Incorrect cuff size for the patient's arm circumference.", S["BulletBody"])),
            ListItem(Paragraph("Cuff positioned more than 2–3 cm from the elbow.", S["BulletBody"])),
            ListItem(Paragraph("Cold ambient temperature causing vasoconstriction.", S["BulletBody"])),
            ListItem(Paragraph("Cardiac arrhythmias (see Section 1.2 Contraindications).", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        PageBreak(),
    ]

    # Section 7 – Maintenance
    els += [
        h1("7. Maintenance and Troubleshooting"),
        hr(),

        h2("7.1 Cleaning and Disinfection"),
        body("Clean the main unit with a soft, slightly damp cloth. Do not use alcohol-based solutions, "
             "solvents, or abrasive cleaners directly on the main unit casing. "
             "The cuff fabric may be hand-washed with mild soap and water; ensure it is completely dry before use. "
             "Do not machine wash the cuff."),

        h2("7.2 Storage"),
        body("Store the device in the original carrying case, away from direct sunlight, extreme temperatures "
             "(below 0°C or above 45°C), and high humidity (above 85% RH). "
             "Remove batteries for storage periods exceeding 3 months."),

        h2("7.3 Calibration"),
        body("The CT-200 requires calibration verification every 2 years or after any significant impact or drop. "
             "Calibration must be performed by a Tri9T-authorised service centre. "
             "A calibration sticker is affixed to the underside of the main unit showing the last verification date."),

        h2("7.4 Troubleshooting"),
        body("Common issues and solutions:"),
        Table(
            [
                [Paragraph("Symptom", S["TableHeader"]),
                 Paragraph("Possible Cause", S["TableHeader"]),
                 Paragraph("Action", S["TableHeader"])],
                ["Device will not turn on",     "Dead/missing batteries",         "Replace batteries or connect AC adapter"],
                ["Display shows E1",            "Cuff not connected",             "Check cuff connector and re-seat"],
                ["Display shows E2",            "Motion artifact during reading", "Repeat measurement; remain still"],
                ["Display shows E3",            "Over-pressurisation (>300 mmHg)","Rest 2 min; repeat. If persists, contact service"],
                ["Display shows E4",            "Cuff too loose or slipped",      "Re-apply cuff and repeat"],
                ["Readings inconsistent",       "Incorrect cuff fit or posture",  "Review Section 4.4 and 6.3"],
                ["IHB indicator appears",       "Irregular pulse detected",       "Consult a healthcare provider"],
                ["Bluetooth not connecting",    "Device not in pairing mode",     "Hold MEMORY 5 sec to enter pairing mode"],
            ],
            colWidths=[1.8*inch, 2.2*inch, 2.4*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("WORDWRAP",   (0, 0), (-1, -1), True),
            ]),
        ),
        sp(10),
        PageBreak(),
    ]

    # Section 8 – Error Codes (DUPLICATE HEADING EDGE CASE: "8. Error Codes" appears in TOC and here)
    els += [
        h1("8. Error Codes"),
        hr(),
        body("The following table provides a complete reference for all error codes displayed by the CT-200. "
             "Codes E1–E4 are also described in Section 7.4. Codes E5–E9 are device-internal and will require service centre attention."),
        Table(
            [
                [Paragraph("Code", S["TableHeader"]),
                 Paragraph("Description", S["TableHeader"]),
                 Paragraph("Auto-Recovery", S["TableHeader"]),
                 Paragraph("Service Required", S["TableHeader"])],
                ["E1", "Cuff not detected",                              "No",      "No"],
                ["E2", "Motion artifact / measurement cancelled",        "Yes",     "No"],
                ["E3", "Over-pressurisation (>300 mmHg); auto-deflate", "Yes",     "No (if isolated)"],
                ["E4", "Cuff displacement detected",                    "No",      "No"],
                ["E5", "Pressure sensor failure",                        "No",      "Yes"],
                ["E6", "Oscillometric algorithm timeout",                "No",      "Yes"],
                ["E7", "Memory read/write failure",                      "No",      "Yes"],
                ["E8", "Bluetooth module error",                         "Partial", "No (restart)"],
                ["E9", "Internal clock failure",                         "No",      "Yes"],
            ],
            colWidths=[0.6*inch, 2.8*inch, 1.3*inch, 1.7*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",      (0, 1), (1, -1), "LEFT"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        sp(10),

        # EDGE CASE: subsection labelled "Error Codes" — same heading text as parent, different level
        h2("8.1 Error Codes During Startup"),
        body("If an error code is displayed immediately upon power-on, it typically indicates a persistent hardware fault. "
             "Codes E5, E7, and E9 displayed at startup require mandatory service centre inspection before further use. "
             "Do not attempt to use the device if any of these codes appear at startup."),
        PageBreak(),
    ]

    # Section 9 – Technical Specifications
    els += [
        h1("9. Technical Specifications"),
        hr(),

        h2("9.1 Measurement Method"),
        body("Oscillometric method, fully automated, upper arm."),

        h2("9.2 Measurement Range"),
        body("Blood Pressure: 20–280 mmHg. Pulse Rate: 40–199 bpm."),

        h2("9.3 Accuracy"),
        body("±3 mmHg (blood pressure); ±5% of reading (pulse rate). See Section 6 for clinical validation details."),

        h2("9.4 Power Supply"),
        body("4 × AA/LR6 alkaline batteries (included), or DC 6V/1A via AC adapter (included). "
             "Battery life: approximately 300 measurements. Low-battery warning displayed when approximately "
             "30 measurements remain."),

        h2("9.5 Environmental Conditions"),
        Table(
            [
                [Paragraph("Condition", S["TableHeader"]), Paragraph("Operating", S["TableHeader"]), Paragraph("Storage/Transport", S["TableHeader"])],
                ["Temperature", "10°C to 40°C", "−20°C to 55°C"],
                ["Relative Humidity", "15% to 85% RH (non-condensing)", "10% to 95% RH (non-condensing)"],
                ["Atmospheric Pressure", "700–1060 hPa", "500–1060 hPa"],
            ],
            colWidths=[2.0*inch, 2.3*inch, 2.1*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        sp(10),

        h2("9.6 Physical Characteristics"),
        body("Main unit: 135 × 95 × 55 mm, 280 g (without batteries). "
             "Standard cuff: 22–42 cm arm circumference. Tube length: 60 cm."),

        h2("9.7 Wireless Interface"),
        body("Bluetooth 5.0 LE, HDP profile. Range: up to 10 m line-of-sight. "
             "USB: micro-USB, USB 2.0 Full-Speed."),
        PageBreak(),
    ]

    # Section 10 – Regulatory
    els += [
        h1("10. Regulatory and Compliance Information"),
        hr(),

        h2("10.1 Regulatory Approvals"),
        body("The CT-200 has received the following regulatory approvals:"),
        ListFlowable([
            ListItem(Paragraph("CE Mark (MDR 2017/745, Class IIa)", S["BulletBody"])),
            ListItem(Paragraph("FDA 510(k) clearance (K-number: K240987)", S["BulletBody"])),
            ListItem(Paragraph("Health Canada Class II Medical Device Licence", S["BulletBody"])),
            ListItem(Paragraph("TGA (Australia) ARTG Entry", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),

        h2("10.2 Standards Compliance"),
        body("The device has been designed and tested to comply with the following standards:"),
        ListFlowable([
            ListItem(Paragraph("IEC 60601-1:2005+AMD1:2012+AMD2:2020 (General requirements for basic safety and essential performance)", S["BulletBody"])),
            ListItem(Paragraph("IEC 60601-1-2:2014+AMD1:2020 (Electromagnetic compatibility)", S["BulletBody"])),
            ListItem(Paragraph("IEC 60601-2-30:2009+AMD1:2013 (Automated non-invasive sphygmomanometers)", S["BulletBody"])),
            ListItem(Paragraph("ISO 81060-2:2018 (Clinical validation)", S["BulletBody"])),
            ListItem(Paragraph("ISO 15223-1:2021 (Medical device symbols)", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),

        h2("10.3 Manufacturer Information"),
        body("Tri9T Medical Devices Inc., 4500 Innovation Blvd, Suite 300, Toronto, ON M5V 2H1, Canada. "
             "support@tri9t-medical.com | +1-800-TRI9T-MD"),
        PageBreak(),
    ]

    # Appendix A – Glossary
    els += [
        h1("Appendix A: Glossary"),
        hr(),
        Table(
            [
                [Paragraph("Term", S["TableHeader"]), Paragraph("Definition", S["TableHeader"])],
                ["Systolic BP",      "The peak pressure in the arteries during a heartbeat (measured in mmHg)."],
                ["Diastolic BP",     "The pressure in the arteries between heartbeats (measured in mmHg)."],
                ["Oscillometric",    "A measurement method that detects oscillations in arterial wall movement caused by blood flow."],
                ["IHB",             "Irregular Heartbeat indicator — flagged when the device detects rhythm irregularity."],
                ["mmHg",            "Millimetres of mercury — the standard unit for blood pressure measurement."],
                ["ISO 81060-2",     "International standard specifying requirements for clinical validation of automated BP monitors."],
                ["EMC",             "Electromagnetic Compatibility — the ability of a device to function correctly in its electromagnetic environment."],
                ["HDP",             "Health Device Profile — a Bluetooth profile for medical device data exchange."],
            ],
            colWidths=[1.6*inch, 4.8*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ]),
        ),
    ]

    return els


# ─── v2 content – selective changes to test versioning and staleness ──────────

def v2_content():
    """
    v2 changes (intentionally limited so most nodes are UNCHANGED):
    1. Section 2.2: Cuff Pressure Safety – threshold changed from 300 to 320 mmHg, E3 response time changed from 2 s to 1 s.
    2. Section 5.1: 'approximately 30–60 seconds' changed to 'approximately 25–45 seconds'.
    3. Section 7.4: New troubleshooting row added ('Display shows E8').
    4. Section 9.4: Battery life changed from 300 to 350 measurements.
    5. New subsection 10.4 added: Post-Market Surveillance.
    6. Section 6.1 accuracy table: BP accuracy tightened to ±2 mmHg.
    """
    els = []

    # Cover
    els += [
        sp(60),
        Paragraph("CardioTrack CT-200", S["DocTitle"]),
        Paragraph("Home Blood Pressure Monitor", S["DocSubtitle"]),
        Paragraph("User Manual &amp; Technical Reference", S["DocSubtitle"]),
        sp(4),
        Paragraph("Version 2.0 | Document ID: CT200-MAN-001 | Rev. 2026-09", S["DocSubtitle"]),
        Paragraph("Tri9T Medical Devices Inc. | Confidential", S["DocSubtitle"]),
        PageBreak(),
    ]

    # TOC
    els += [
        h1("Table of Contents"),
        body("1. Introduction and Intended Use ............................... 3"),
        body("2. Safety Warnings and Precautions ............................. 4"),
        body("3. Device Description and Components ........................... 6"),
        body("4. Installation and Setup ...................................... 8"),
        body("5. Operating Instructions ...................................... 10"),
        body("6. Measurement Accuracy and Clinical Validation ................ 13"),
        body("7. Maintenance and Troubleshooting ............................. 15"),
        body("8. Error Codes ................................................. 17"),
        body("9. Technical Specifications .................................... 19"),
        body("10. Regulatory and Compliance Information ...................... 21"),
        body("Appendix A: Glossary ........................................... 23"),
        PageBreak(),
    ]

    # Section 1 – identical
    els += [
        h1("1. Introduction and Intended Use"),
        hr(),
        body("The CardioTrack CT-200 is a non-invasive automated oscillometric blood pressure monitor "
             "intended for home use by adult patients under the supervision of a healthcare professional. "
             "It measures systolic and diastolic blood pressure and pulse rate using the oscillometric method."),
        body("This device is intended for use on the upper arm of adults aged 18 years and older. "
             "It is not intended to replace clinical-grade sphygmomanometers used by trained medical staff."),
        h2("1.1 Indications for Use"),
        body("The CT-200 is indicated for use in the following clinical contexts:"),
        ListFlowable([
            ListItem(Paragraph("Home blood pressure monitoring for hypertensive patients.", S["BulletBody"])),
            ListItem(Paragraph("Ambulatory blood pressure tracking as part of a physician-prescribed regimen.", S["BulletBody"])),
            ListItem(Paragraph("Wellness monitoring for individuals at risk of cardiovascular disease.", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        h2("1.2 Contraindications"),
        body("Do not use the CT-200 in the following situations:"),
        ListFlowable([
            ListItem(Paragraph("Patients with cardiac arrhythmias, as irregular pulse may affect measurement accuracy.", S["BulletBody"])),
            ListItem(Paragraph("Patients with arteriovenous fistula or dialysis shunts in the measurement arm.", S["BulletBody"])),
            ListItem(Paragraph("During infusion or IV administration in the measurement arm.", S["BulletBody"])),
            ListItem(Paragraph("Patients with Raynaud's disease or other severe circulation disorders.", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        h2("1.3 Patient Population"),
        body("This device is validated for adult patients with an upper arm circumference between 22 cm and 42 cm. "
             "A separate paediatric cuff is available but is out of scope for this manual. "
             "Do not use on neonates or infants."),
        note("The CT-200 has NOT been validated for use during pregnancy or in patients with pre-eclampsia. "
             "Clinical judgement should be exercised."),
        PageBreak(),
    ]

    # Section 2 – CHANGED: 2.2 threshold changed 300→320, E3 time 2s→1s
    els += [
        h1("2. Safety Warnings and Precautions"),
        hr(),
        warn("Do not use near high-frequency surgical equipment, MRI machines, or defibrillators. "
             "Electromagnetic interference may cause inaccurate readings or device malfunction."),
        warn("Do not attempt to disassemble, modify, or repair the device. Unauthorized modification "
             "voids the warranty and may create electrical or mechanical hazards."),
        h2("2.1 Electrical Safety"),
        body("The CT-200 operates on 4 × AA alkaline batteries (IEC LR6) or via the included AC adapter (100–240 V AC, 50/60 Hz). "
             "Never use both power sources simultaneously. Disconnect the AC adapter before replacing batteries."),
        body("The device complies with IEC 60601-1 requirements for electrical safety in medical equipment. "
             "The enclosure is rated IP21 (drip-proof) but is not waterproof. Do not immerse in liquids."),

        # *** CHANGED ***
        h2("2.2 Cuff Pressure Safety"),
        body("The device automatically deflates if cuff pressure exceeds 320 mmHg. "
             "If over-pressurisation occurs during a measurement, the device will display error code E3 "
             "and auto-deflate within 1 second. Continuous re-inflation attempts without a rest period "
             "of at least 2 minutes may cause discomfort or circulatory impairment."),

        h2("2.3 Electromagnetic Compatibility"),
        body("The CT-200 has been tested for EMC compliance in accordance with IEC 60601-1-2 (4th edition). "
             "The device is classified as Equipment Class B, suitable for use in home and hospital environments. "
             "Portable RF communications equipment (e.g., mobile phones) should be kept at least 30 cm from the device during measurements."),
        h2("2.4 Disposal and Environmental Considerations"),
        body("Do not dispose of this device with household waste. Dispose of batteries in accordance "
             "with local regulations. The device contains recyclable materials; contact Tri9T Medical "
             "Devices for return and recycling instructions."),
        PageBreak(),
    ]

    # Section 3 – identical
    els += [
        h1("3. Device Description and Components"),
        hr(),
        body("The CT-200 system consists of the following components:"),
        h2("3.1 Main Unit"),
        body("The main unit houses the measurement electronics, display, and control interface. "
             "Dimensions: 135 mm × 95 mm × 55 mm. Weight (without batteries): 280 g."),
        body("The front panel includes:"),
        ListFlowable([
            ListItem(Paragraph("3.5-inch LCD display (128×64 pixels) with backlight.", S["BulletBody"])),
            ListItem(Paragraph("START/STOP button (large, tactile, blue).", S["BulletBody"])),
            ListItem(Paragraph("MEMORY button for reviewing stored readings.", S["BulletBody"])),
            ListItem(Paragraph("CLOCK SET button for date/time configuration.", S["BulletBody"])),
            ListItem(Paragraph("Power indicator LED (green: on; red: low battery).", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        cap("Figure 3-1: Front panel layout of the CT-200 main unit. See Appendix B for detailed diagram."),
        h2("3.2 Cuff and Tubing"),
        body("The standard cuff (model CT200-CF-M) fits upper arms 22–42 cm in circumference. "
             "The cuff is constructed from washable nylon fabric with a latex-free internal bladder. "
             "The air tube length is 60 cm with a standard Luer-type connector."),
        note("Replacement cuffs must be sourced from Tri9T Medical Devices or an authorised distributor. "
             "Third-party cuffs may affect measurement accuracy and void the warranty."),
        h2("3.3 Connectivity"),
        body("The CT-200 includes a micro-USB port for data export to a PC via the CardioLink software (Windows 10/11, macOS 12+). "
             "Bluetooth 5.0 LE is available for wireless data transfer to the CardioTrack mobile application "
             "(iOS 14+ / Android 9+). Data is transmitted using the Bluetooth Health Device Profile (HDP)."),
        h2("3.4 Memory and Data Storage"),
        body("The device stores up to 120 readings (60 per user slot in a 2-user configuration). "
             "Each reading includes: date, time, systolic BP, diastolic BP, pulse rate, and an irregular heartbeat (IHB) indicator. "
             "Memory is retained when batteries are replaced, provided replacement is completed within 60 seconds."),
        h3("3.4.1 Data Security and Privacy"),
        body("No patient-identifiable information is stored on the device. "
             "All data exported via USB or Bluetooth is in raw measurement format (not encrypted by the device). "
             "Healthcare providers should apply appropriate data-handling policies when transferring readings."),
        PageBreak(),
    ]

    # Section 4 – identical
    els += [
        h1("4. Installation and Setup"),
        hr(),
        h2("4.1 Battery Installation"),
        body("Open the battery compartment on the bottom of the main unit by sliding the cover in the direction "
             "indicated by the arrow. Insert 4 × AA batteries observing correct polarity (marked inside the compartment). "
             "Replace the cover until it clicks into place."),
        warn("Use only fresh alkaline batteries. Do not mix old and new batteries or batteries of different types. "
             "Remove batteries if the device will not be used for more than 3 months."),
        h2("4.2 AC Adapter Connection"),
        body("Connect the AC adapter to the DC IN port on the right side of the main unit, then plug the adapter "
             "into a standard AC outlet. The power LED will illuminate green. The battery icon on the display will "
             "be replaced by a plug icon when AC power is active."),
        h2("4.3 Date and Time Setup"),
        body("On first use, the display will show the time setup screen. Use the CLOCK SET button to enter setup mode, "
             "then use START/STOP to cycle through digits and MEMORY to confirm each field. "
             "Fields: Year → Month → Day → Hour → Minute. Press CLOCK SET again to exit."),
        h2("4.4 Cuff Fitting"),
        body("Proper cuff placement is critical for accurate readings. Follow these steps:"),
        ListFlowable([
            ListItem(Paragraph("Rest for 5 minutes before measuring. Avoid caffeine, smoking, or strenuous exercise for 30 minutes prior.", S["BulletBody"])),
            ListItem(Paragraph("Sit in a chair with back supported. Keep feet flat on the floor.", S["BulletBody"])),
            ListItem(Paragraph("Place the left arm on a flat surface at heart level. Palm facing upward.", S["BulletBody"])),
            ListItem(Paragraph("Wrap the cuff around the upper arm, 2–3 cm above the elbow. The artery marker (▷) should align with the brachial artery.", S["BulletBody"])),
            ListItem(Paragraph("Ensure the cuff is snug but not tight — you should be able to slide two fingers under it.", S["BulletBody"])),
            ListItem(Paragraph("Connect the air tube to the main unit.", S["BulletBody"])),
        ], bulletType='1', leftIndent=30),
        sp(),
        cap("Figure 4-1: Correct cuff placement on the upper left arm."),
        PageBreak(),
    ]

    # Section 5 – CHANGED: 5.1 measurement time 30-60s → 25-45s
    els += [
        h1("5. Operating Instructions"),
        hr(),

        # *** CHANGED ***
        h2("5.1 Taking a Measurement"),
        body("Once the device is set up (see Section 4), press the START/STOP button to begin a measurement. "
             "The cuff will automatically inflate. Remain still and do not talk during inflation and measurement. "
             "After approximately 25–45 seconds, the cuff will deflate and the reading will be displayed."),
        body("The display shows: systolic (top), diastolic (bottom), and pulse rate (right). "
             "A WHO risk indicator (colour bar) is shown if the optional display mode is enabled."),

        h2("5.2 Reading the Results"),
        body("Blood pressure categories per WHO/ESH 2023 guidelines:"),
        Table(
            [
                [Paragraph("Category", S["TableHeader"]),
                 Paragraph("Systolic (mmHg)", S["TableHeader"]),
                 Paragraph("Diastolic (mmHg)", S["TableHeader"])],
                ["Optimal",         "< 120",    "< 80"],
                ["Normal",          "120–129",  "80–84"],
                ["High Normal",     "130–139",  "85–89"],
                ["Grade 1 HT",      "140–159",  "90–99"],
                ["Grade 2 HT",      "160–179",  "100–109"],
                ["Grade 3 HT",      "≥ 180",    "≥ 110"],
            ],
            colWidths=[2.4*inch, 2.0*inch, 2.0*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        sp(10),
        h2("5.3 Irregular Heartbeat Detection"),
        body("If the device detects an irregular heartbeat pattern during measurement, the IHB symbol (♥?) "
             "will appear on the display. This is an indication only — it does not constitute a clinical diagnosis. "
             "Consult a healthcare provider if this symbol appears frequently."),
        h2("5.4 Memory Recall"),
        body("Press the MEMORY button to display stored readings. The display will show the reading number, "
             "date/time, and measurement values. Readings are stored in chronological order, with the most recent first. "
             "To scroll through readings, press MEMORY repeatedly. Press START/STOP to return to normal mode."),
        h2("5.5 Multi-User Mode"),
        body("The CT-200 supports two user profiles (User 1 and User 2). "
             "To switch users, hold the MEMORY button for 3 seconds. "
             "Each user has an independent 60-reading memory. "
             "User profiles do not store personal identifiers — they are simply two separate memory banks."),
        h3("5.5.1 Switching Users During a Measurement"),
        body("Do not attempt to switch user profiles during an active measurement. "
             "If the MEMORY button is held during cuff inflation or measurement, the action will be ignored "
             "and the measurement will continue unaffected."),
        PageBreak(),
    ]

    # Section 6 – CHANGED: accuracy ±3 mmHg → ±2 mmHg
    els += [
        h1("6. Measurement Accuracy and Clinical Validation"),
        hr(),

        # *** CHANGED accuracy spec ***
        h2("6.1 Accuracy Specifications"),
        body("The CT-200 has been validated in accordance with ISO 81060-2:2018 (Non-invasive sphygmomanometers — "
             "Clinical validation of automated measurement type). The following accuracy specifications apply:"),
        Table(
            [
                [Paragraph("Parameter", S["TableHeader"]),
                 Paragraph("Specification", S["TableHeader"]),
                 Paragraph("Standard", S["TableHeader"])],
                ["Blood Pressure (BP)",   "±2 mmHg or 2% of reading", "ISO 81060-2"],
                ["Pulse Rate",            "±5% of reading",           "ISO 81060-2"],
                ["Cuff Pressure Range",   "0–320 mmHg",               "IEC 60601-2-30"],
                ["Static Pressure Acc.",  "±2 mmHg",                  "IEC 60601-2-30"],
            ],
            colWidths=[2.4*inch, 2.3*inch, 1.7*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        sp(10),

        h2("6.2 Clinical Study Results"),
        body("A clinical validation study was conducted at St. Michael's Cardiovascular Institute (n=85 subjects, "
             "age range 21–78, BMI 18.5–35.2 kg/m²) under the supervision of a registered cardiologist. "
             "The study protocol was reviewed and approved by the institutional ethics board."),
        body("Study outcomes (per ISO 81060-2 grading criteria):"),
        ListFlowable([
            ListItem(Paragraph("Mean difference (device vs. reference): −0.8 mmHg systolic, +1.1 mmHg diastolic.", S["BulletBody"])),
            ListItem(Paragraph("Standard deviation of differences: 3.7 mmHg systolic, 3.4 mmHg diastolic.", S["BulletBody"])),
            ListItem(Paragraph("Grade A classification achieved for both systolic and diastolic measurements.", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        h2("6.3 Factors Affecting Accuracy"),
        body("The following factors may affect measurement accuracy and should be considered when interpreting results:"),
        ListFlowable([
            ListItem(Paragraph("Body movement or talking during measurement.", S["BulletBody"])),
            ListItem(Paragraph("Incorrect cuff size for the patient's arm circumference.", S["BulletBody"])),
            ListItem(Paragraph("Cuff positioned more than 2–3 cm from the elbow.", S["BulletBody"])),
            ListItem(Paragraph("Cold ambient temperature causing vasoconstriction.", S["BulletBody"])),
            ListItem(Paragraph("Cardiac arrhythmias (see Section 1.2 Contraindications).", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        PageBreak(),
    ]

    # Section 7 – CHANGED: extra troubleshooting row + note
    els += [
        h1("7. Maintenance and Troubleshooting"),
        hr(),
        h2("7.1 Cleaning and Disinfection"),
        body("Clean the main unit with a soft, slightly damp cloth. Do not use alcohol-based solutions, "
             "solvents, or abrasive cleaners directly on the main unit casing. "
             "The cuff fabric may be hand-washed with mild soap and water; ensure it is completely dry before use. "
             "Do not machine wash the cuff."),
        h2("7.2 Storage"),
        body("Store the device in the original carrying case, away from direct sunlight, extreme temperatures "
             "(below 0°C or above 45°C), and high humidity (above 85% RH). "
             "Remove batteries for storage periods exceeding 3 months."),
        h2("7.3 Calibration"),
        body("The CT-200 requires calibration verification every 2 years or after any significant impact or drop. "
             "Calibration must be performed by a Tri9T-authorised service centre. "
             "A calibration sticker is affixed to the underside of the main unit showing the last verification date."),
        h2("7.4 Troubleshooting"),
        body("Common issues and solutions:"),
        Table(
            [
                [Paragraph("Symptom", S["TableHeader"]),
                 Paragraph("Possible Cause", S["TableHeader"]),
                 Paragraph("Action", S["TableHeader"])],
                ["Device will not turn on",     "Dead/missing batteries",         "Replace batteries or connect AC adapter"],
                ["Display shows E1",            "Cuff not connected",             "Check cuff connector and re-seat"],
                ["Display shows E2",            "Motion artifact during reading", "Repeat measurement; remain still"],
                ["Display shows E3",            "Over-pressurisation (>320 mmHg)","Rest 2 min; repeat. If persists, contact service"],
                ["Display shows E4",            "Cuff too loose or slipped",      "Re-apply cuff and repeat"],
                ["Display shows E8",            "Bluetooth module error",         "Restart device; re-pair via CardioTrack app"],  # NEW ROW
                ["Readings inconsistent",       "Incorrect cuff fit or posture",  "Review Section 4.4 and 6.3"],
                ["IHB indicator appears",       "Irregular pulse detected",       "Consult a healthcare provider"],
                ["Bluetooth not connecting",    "Device not in pairing mode",     "Hold MEMORY 5 sec to enter pairing mode"],
            ],
            colWidths=[1.8*inch, 2.2*inch, 2.4*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        sp(10),
        PageBreak(),
    ]

    # Section 8 – identical
    els += [
        h1("8. Error Codes"),
        hr(),
        body("The following table provides a complete reference for all error codes displayed by the CT-200. "
             "Codes E1–E4 are also described in Section 7.4. Codes E5–E9 are device-internal and will require service centre attention."),
        Table(
            [
                [Paragraph("Code", S["TableHeader"]),
                 Paragraph("Description", S["TableHeader"]),
                 Paragraph("Auto-Recovery", S["TableHeader"]),
                 Paragraph("Service Required", S["TableHeader"])],
                ["E1", "Cuff not detected",                              "No",      "No"],
                ["E2", "Motion artifact / measurement cancelled",        "Yes",     "No"],
                ["E3", "Over-pressurisation (>320 mmHg); auto-deflate", "Yes",     "No (if isolated)"],
                ["E4", "Cuff displacement detected",                    "No",      "No"],
                ["E5", "Pressure sensor failure",                        "No",      "Yes"],
                ["E6", "Oscillometric algorithm timeout",                "No",      "Yes"],
                ["E7", "Memory read/write failure",                      "No",      "Yes"],
                ["E8", "Bluetooth module error",                         "Partial", "No (restart)"],
                ["E9", "Internal clock failure",                         "No",      "Yes"],
            ],
            colWidths=[0.6*inch, 2.8*inch, 1.3*inch, 1.7*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",      (0, 1), (1, -1), "LEFT"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        sp(10),
        h2("8.1 Error Codes During Startup"),
        body("If an error code is displayed immediately upon power-on, it typically indicates a persistent hardware fault. "
             "Codes E5, E7, and E9 displayed at startup require mandatory service centre inspection before further use. "
             "Do not attempt to use the device if any of these codes appear at startup."),
        PageBreak(),
    ]

    # Section 9 – CHANGED: 9.4 battery life 300→350
    els += [
        h1("9. Technical Specifications"),
        hr(),
        h2("9.1 Measurement Method"),
        body("Oscillometric method, fully automated, upper arm."),
        h2("9.2 Measurement Range"),
        body("Blood Pressure: 20–280 mmHg. Pulse Rate: 40–199 bpm."),
        h2("9.3 Accuracy"),
        body("±2 mmHg (blood pressure); ±5% of reading (pulse rate). See Section 6 for clinical validation details."),

        # *** CHANGED ***
        h2("9.4 Power Supply"),
        body("4 × AA/LR6 alkaline batteries (included), or DC 6V/1A via AC adapter (included). "
             "Battery life: approximately 350 measurements. Low-battery warning displayed when approximately "
             "30 measurements remain."),

        h2("9.5 Environmental Conditions"),
        Table(
            [
                [Paragraph("Condition", S["TableHeader"]), Paragraph("Operating", S["TableHeader"]), Paragraph("Storage/Transport", S["TableHeader"])],
                ["Temperature", "10°C to 40°C", "−20°C to 55°C"],
                ["Relative Humidity", "15% to 85% RH (non-condensing)", "10% to 95% RH (non-condensing)"],
                ["Atmospheric Pressure", "700–1060 hPa", "500–1060 hPa"],
            ],
            colWidths=[2.0*inch, 2.3*inch, 2.1*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        sp(10),
        h2("9.6 Physical Characteristics"),
        body("Main unit: 135 × 95 × 55 mm, 280 g (without batteries). "
             "Standard cuff: 22–42 cm arm circumference. Tube length: 60 cm."),
        h2("9.7 Wireless Interface"),
        body("Bluetooth 5.0 LE, HDP profile. Range: up to 10 m line-of-sight. "
             "USB: micro-USB, USB 2.0 Full-Speed."),
        PageBreak(),
    ]

    # Section 10 – CHANGED: new 10.4 subsection added
    els += [
        h1("10. Regulatory and Compliance Information"),
        hr(),
        h2("10.1 Regulatory Approvals"),
        body("The CT-200 has received the following regulatory approvals:"),
        ListFlowable([
            ListItem(Paragraph("CE Mark (MDR 2017/745, Class IIa)", S["BulletBody"])),
            ListItem(Paragraph("FDA 510(k) clearance (K-number: K240987)", S["BulletBody"])),
            ListItem(Paragraph("Health Canada Class II Medical Device Licence", S["BulletBody"])),
            ListItem(Paragraph("TGA (Australia) ARTG Entry", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        h2("10.2 Standards Compliance"),
        body("The device has been designed and tested to comply with the following standards:"),
        ListFlowable([
            ListItem(Paragraph("IEC 60601-1:2005+AMD1:2012+AMD2:2020 (General requirements for basic safety and essential performance)", S["BulletBody"])),
            ListItem(Paragraph("IEC 60601-1-2:2014+AMD1:2020 (Electromagnetic compatibility)", S["BulletBody"])),
            ListItem(Paragraph("IEC 60601-2-30:2009+AMD1:2013 (Automated non-invasive sphygmomanometers)", S["BulletBody"])),
            ListItem(Paragraph("ISO 81060-2:2018 (Clinical validation)", S["BulletBody"])),
            ListItem(Paragraph("ISO 15223-1:2021 (Medical device symbols)", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        h2("10.3 Manufacturer Information"),
        body("Tri9T Medical Devices Inc., 4500 Innovation Blvd, Suite 300, Toronto, ON M5V 2H1, Canada. "
             "support@tri9t-medical.com | +1-800-TRI9T-MD"),

        # NEW in v2
        h2("10.4 Post-Market Surveillance"),
        body("Tri9T Medical Devices conducts ongoing post-market surveillance (PMS) in accordance with MDR 2017/745 Article 83 "
             "and FDA 21 CFR Part 803. Healthcare providers and users are encouraged to report adverse events, near-misses, "
             "or unexpected device behaviour via the following channels:"),
        ListFlowable([
            ListItem(Paragraph("Online: https://tri9t-medical.com/report", S["BulletBody"])),
            ListItem(Paragraph("Email: pms@tri9t-medical.com", S["BulletBody"])),
            ListItem(Paragraph("Phone: +1-800-TRI9T-MD (24/7 safety hotline)", S["BulletBody"])),
        ], bulletType='bullet', leftIndent=30),
        sp(),
        body("PMS data feeds into the periodic safety update reports (PSURs) filed annually with the relevant regulatory authorities. "
             "Device identifiers (UDI-DI: 0614141000168) are used to trace field reports back to specific production batches."),
        PageBreak(),
    ]

    # Appendix A – identical
    els += [
        h1("Appendix A: Glossary"),
        hr(),
        Table(
            [
                [Paragraph("Term", S["TableHeader"]), Paragraph("Definition", S["TableHeader"])],
                ["Systolic BP",      "The peak pressure in the arteries during a heartbeat (measured in mmHg)."],
                ["Diastolic BP",     "The pressure in the arteries between heartbeats (measured in mmHg)."],
                ["Oscillometric",    "A measurement method that detects oscillations in arterial wall movement caused by blood flow."],
                ["IHB",             "Irregular Heartbeat indicator — flagged when the device detects rhythm irregularity."],
                ["mmHg",            "Millimetres of mercury — the standard unit for blood pressure measurement."],
                ["ISO 81060-2",     "International standard specifying requirements for clinical validation of automated BP monitors."],
                ["EMC",             "Electromagnetic Compatibility — the ability of a device to function correctly in its electromagnetic environment."],
                ["HDP",             "Health Device Profile — a Bluetooth profile for medical device data exchange."],
            ],
            colWidths=[1.6*inch, 4.8*inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ]),
        ),
    ]

    return els


# ─── build PDFs ───────────────────────────────────────────────────────────────

def build_pdf(path, content_fn):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=0.9*inch, leftMargin=0.9*inch,
        topMargin=0.9*inch, bottomMargin=0.9*inch,
        title="CardioTrack CT-200 User Manual",
        author="Tri9T Medical Devices Inc.",
    )
    doc.build(content_fn())
    print(f"  Generated: {path}")


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    print("Generating CT-200 PDFs …")
    build_pdf(os.path.join("data", "ct200_manual_v1.pdf"), v1_content)
    build_pdf(os.path.join("data", "ct200_manual_v2.pdf"), v2_content)
    print("Done.")

