# Failed-Question Review — for Clinical Pharmacist

**Total questions evaluated:** 75 scoreable (45 canonical from the 4 client CSVs + 30 distilled new clinical scenarios)
**Failures requiring review:** 17
**Production stack:** Voyage `voyage-4-large` retrieval + Claude Haiku 4.5 + few-shot system prompt v2 + `temperature=0`

**How to review each entry:**
1. Read the question + the clinical editor's expected answer.
2. Read the chatbot's actual answer.
3. Decide: is the answer **clinically acceptable** for a licensed pharmacist to act on?
4. Tick the box at the end of each entry: ☐ Clinically OK  ☐ Needs revision  ☐ Dangerous
5. Add a one-line note on what's specifically wrong, if anything.

The 'auto-judge reason' line shows why our automated LLM-judge marked it as a failure — sometimes the judge is over-strict and a human reviewer disagrees; we want your independent verdict.

---

## Summary table (read this first)

| # | ID | 🚨 | Full question | Expected (per clinical editor) | Why our judge flagged it |
|---|---|---|---|---|---|
| 1 | **CF-12** |  | Q5: What is the duration of antibiotic therapy in rhinosinusitis? | See Table 2: First-line: Adults: 5-7 days; Children: 10 days. Failure of Tx: adults: 5-10 days; children: 10 days | The answer fails criterion (b) by making the specific mistake identified in NEGATIVE FEEDBACK. For children who fail first-line therapy, the answer states 'treat for 5–10 days' without clarifying that children should receive the full 10-day duration. This creates ambiguity that a clinician could interpret as 5 days being acceptable for a child, directly violating the safety concern that 'a child w |
| 2 | **CF-14** |  | Q2: How do I manage medications that prolong QT | Expecting list of risk factors to consider, perhaps treatment options | The answer fails criterion (b) by including an external resource reference that the negative feedback explicitly states should NOT be included. The negative feedback specifies: 'External link that provides list of drugs at risk of QT prolongation not included.' The answer contains a detailed drug list (antiarrhythmics, macrolides, quinolones, antidepressants, antiemetics, antifungals, antipsychoti |
| 3 | **NQ-001** |  | A 28-year-old pregnant woman (second trimester) with a urinary tract infection tests positive for Group B Streptococcus. What antibiotic is preferred, and what is the standard dosing during pregnancy? | Answer must specify penicillin G or amoxicillin as first-line for GBS UTI in pregnancy, acknowledge safety in pregnancy, and provide appropriate dosing (typically amoxicillin 500 mg TID or penicillin G dosing). Must address that treatment is mandatory to prevent neonatal transmission. | (a) FAILED: The answer does not specify penicillin G or amoxicillin as first-line for GBS UTI in pregnancy, does not acknowledge the mandatory nature of GBS eradication to prevent neonatal transmission, and does not provide dosing (amoxicillin 500 mg TID or penicillin G dosing). Instead, it hedges that 'the source does not provide specific guidance' and defers to ID consultation. (b) PASSED: The a |
| 4 | **NQ-002** |  | A 3-year-old child (18 kg) with acute otitis media has a penicillin allergy (rash, non-anaphylactic). What is the appropriate first-line antibiotic and dose? | Answer must recommend cephalosporin (cefixime or cefaclor) as first-line for penicillin-allergic children with otitis media, calculate weight-based dose correctly (~8-10 mg/kg/day for cefixime), and note low cross-reactivity risk with cephalosporins in non-anaphylactic penicillin allergy. | The answer recommends cefuroxime axetil as first-line, but the expected result specifies cefixime or cefaclor as first-line alternatives for penicillin-allergic children with otitis media. While cefuroxime is a valid cephalosporin option, the expected clinical guidance names specific agents (cefixime/cefaclor), and the answer's choice of cefuroxime—a second-generation agent—deviates from the expec |
| 5 | **NQ-003** |  | A 72-year-old male with CKD stage 3b (eGFR 35 mL/min/1.73m²) and hypertension is prescribed lisinopril 10 mg daily. Is dose adjustment needed? What monitoring is required? | Answer must state that lisinopril requires dose reduction at eGFR <60 (typically reduce to 5 mg or adjust interval), explain need for baseline and follow-up K+ and creatinine monitoring (within 1-2 weeks), and describe signs of hyperkalemia or acute kidney injury to watch for. | The answer violates the critical safety requirement in NEGATIVE FEEDBACK by stating 'No dose adjustment is required for lisinopril 10 mg daily' at eGFR 35. The EXPECTED RESULT explicitly requires stating that lisinopril requires dose reduction at eGFR <60 (typically to 5 mg or adjusted interval). This is a direct contradiction of the clinical standard the editor identified as a must-avoid error. |
| 6 | **NQ-004** |  | A 45-year-old woman on warfarin (INR goal 2–3) for atrial fibrillation is prescribed clarithromycin for pneumonia. What is the pharmacokinetic interaction, and how should INR be managed? | Answer must identify that clarithromycin inhibits CYP3A4, increasing warfarin levels and INR, recommend checking INR within 3–5 days of starting clarithromycin, consider alternative antibiotic (e.g., doxycycline or amoxicillin-clavulanate if susceptible), and advise patient on bleeding signs. May mention warfarin dose reduction if clarithromycin necessary. | The answer correctly identifies the CYP3A4 inhibition mechanism and recommends INR monitoring within 3–5 days, which satisfies part of (a). However, it fails the critical safety requirement in (a) by not recommending specific alternative antibiotics (doxycycline or amoxicillin-clavulanate) as stated in EXPECTED, and it omits explicit patient counseling on bleeding signs, which is a safety-critical |
| 7 | **NQ-005** |  | A 68-year-old woman with severe hepatic cirrhosis (Child-Pugh C) presents with hypertension. Is atenolol or metoprolol preferred, and why? What dose adjustment is needed? | Answer must recognize that metoprolol is preferred over atenolol in advanced liver disease (atenolol renally eliminated, metoprolol hepatically metabolized but still requires caution), recommend significant dose reduction (start ~25–50 mg daily), and stress need for careful monitoring of heart rate and blood pressure due to impaired metabolism and risk of hepatic encephalopathy. | (a) FAILED: The answer explicitly declines to recommend metoprolol over atenolol, stating 'the source does not distinguish between atenolol and metoprolol based on hepatic function or recommend a choice between them in cirrhosis.' It then suggests atenolol may be safer due to renal elimination, which contradicts the expected clinical consensus that metoprolol is preferred. (b) FAILED: The answer a |
| 8 | **NQ-006** |  | A 6-month-old infant with fever and suspected bacterial meningitis requires empiric antibiotics. What is the appropriate antibiotic regimen and dosing for this age group? | Answer must specify ceftriaxone + ampicillin (+ vancomycin if resistance concern) with age-appropriate dosing (ceftriaxone ~50 mg/kg/dose IV Q4–6H, ampicillin ~50 mg/kg/dose IV Q4–6H), acknowledge Listeria monocytogenes coverage need, and emphasize meningitis-level dosing (higher than non-meningitis infections). | (a) FAILED: The answer omits ampicillin entirely, which is a critical safety gap for Listeria monocytogenes coverage in infants <3 months (and recommended through 6 months in many guidelines). The expected result explicitly requires 'ceftriaxone + ampicillin (+ vancomycin if resistance concern)' and emphasizes 'acknowledge Listeria monocytogenes coverage need.' The answer provides cefotaxime/vanco |
| 9 | **NQ-007** |  | A 35-year-old woman breastfeeding a 4-month-old is prescribed sertraline 50 mg daily for postpartum depression. Is this safe? What counseling is needed? | Answer must confirm sertraline is preferred SSRI in lactation (minimal infant exposure, well-studied), note that infant receives ~0.5–2% of maternal dose, recommend monitoring infant for drowsiness or poor feeding, and advise that benefits typically outweigh risks. May mention alternatives (paroxetine also acceptable). | The answer fails criterion (b) by recommending citalopram as a first-line option without mentioning its higher infant exposure relative to sertraline. The negative feedback explicitly prohibits 'recommending citalopram without mentioning higher infant exposure.' The answer also lists escitalopram as equivalent without the same caveat. Additionally, the answer omits the specific quantitative reassu |
| 10 | **NQ-008** |  | An 81-year-old woman with mild cognitive impairment and hypertension is on hydrochlorothiazide 25 mg daily. Her recent labs show Na+ 128 mEq/L. What is the likely diagnosis and management? | Answer must identify thiazide-induced hyponatremia (SIADH mechanism), recommend dose reduction or switch to alternative antihypertensive (e.g., ACE-I, calcium channel blocker), explain need for gradual Na+ correction (not >8–10 mEq/L per 24h to avoid osmotic demyelination), and monitor for confusion/falls related to hyponatremia. | The answer fails criterion (a) by omitting the critical safety parameter: the maximum rate of sodium correction (8–10 mEq/L per 24h) to avoid osmotic demyelination syndrome. While the answer mentions 'gradual correction' and names the syndrome, it does not specify the numeric threshold required for safe management. This is a safety-critical numeric threshold that the expected result explicitly req |
| 11 | **NQ-017** |  | A 4-year-old child (16 kg) with severe asthma exacerbation requires IV methylprednisolone. What is the appropriate dose in mg/kg, and what is the total dose in this case? | Answer must provide weight-based dose (typically 1–2 mg/kg/dose IV, often 30 mg/kg/day divided into 4 doses for severe exacerbation, or initial bolus of 1–2 mg/kg), calculate correctly for 16 kg child (16–32 mg per dose, or up to 480 mg/day divided), and specify dosing interval (Q4–6H). | (a) FAILED: The answer provides a maintenance dose of 0.5 mg/kg Q6H (8 mg per dose), which falls below the expected range of 1–2 mg/kg/dose and does not align with the typical severe exacerbation regimen of 30 mg/kg/day divided into 4 doses (7.5 mg/kg per dose Q6H). The induction bolus of 2 mg/kg (32 mg) is appropriate, but the maintenance dosing is clinically suboptimal for severe exacerbation. ( |
| 12 | **NQ-018** |  | A 68-year-old woman on warfarin presents with INR 8.2 (goal 2–3) and no bleeding. What is the appropriate management, and what is the warfarin dose adjustment? | Answer must state that INR 8.2 without bleeding typically requires warfarin discontinuation (1–2 doses) plus vitamin K1 (phytonadione) 2.5 mg PO (not 10 mg, which may cause INR resistance), check INR in 24–48 hours, and resume warfarin at reduced dose when INR <5. Must distinguish from INR >20 or bleeding scenarios. | (a) FAILED: The answer explicitly states the source 'does not provide specific management protocols' and declines to provide the expected clinical content (warfarin discontinuation, vitamin K1 2.5 mg PO dosing, 24–48 hour INR recheck, resume at reduced dose when INR <5). Instead it defers to external guidelines and suggests 'without routine vitamin K'—contradicting the expected standard of care. ( |
| 13 | **NQ-019** |  | A 45-year-old man with gout receives indomethacin for acute flare. What is the typical maximum daily dose, and for how many days is it typically prescribed? | Answer must specify indomethacin max dose of 150–200 mg/day (typically 50 mg TID) for acute gout, duration of 5–7 days (or until symptoms resolve, usually 3–5 days), and note that NSAIDs should be started early in flare and used with gastroprotection if risk factors present. | (a) FAILED: The answer states a maximum daily dose of 175 mg, which falls within the expected 150–200 mg/day range and includes a specific dosing regimen. However, the stated duration of 4 days is below the expected 5–7 days range, and the answer does not explicitly state the typical 50 mg TID dosing or the 5–7 day (or 3–5 days until symptom resolution) duration guidance. (b) The answer does not v |
| 14 | **NQ-028** |  | A 38-year-old woman with migraine without aura asks about using a triptan vs. a nonsteroidal anti-inflammatory drug (NSAID) for acute attack. What is the key distinction in their use? | Answer must explain that NSAIDs (ibuprofen, naproxen) are first-line for mild-to-moderate migraines and tension headaches, while triptans (sumatriptan, rizatriptan) are reserved for moderate-to-severe migraines or when NSAIDs fail. Triptans work via 5-HT1B/1D receptor agonism (vasoconstriction), while NSAIDs reduce inflammation. Triptans contraindicated in coronary artery disease; NSAIDs contraindicated in certain GI/renal conditions. | (a) FAIL: The answer states 'Triptans are considered first-line for moderate to severe migraine attacks' which directly violates the negative feedback instruction 'Stating triptans are first-line.' While the answer does mention NSAIDs for mild-to-moderate migraines and includes severity-based selection, the explicit statement that triptans are first-line contradicts the clinical editor's requireme |
| 15 | **NQ-030** |  | A 35-year-old man with acute bacterial sinusitis (facial pain, nasal congestion, purulent discharge, 5 days duration) asks if he needs an antibiotic or if decongestants alone will help. What is the evidence-based recommendation? | Answer must clarify that acute bacterial sinusitis (confirmed by imaging or clinical criteria like symptom duration >10 days, worsening after initial improvement, or severe symptoms) requires antibiotics (amoxicillin-clavulanate first-line), while early/mild viral sinusitis may resolve with supportive care and decongestants. Nasal saline irrigations and intranasal corticosteroids are adjunctive. This patient's 5-day duration and purulent discharge suggest bacterial infection warranting antibiotics. | The answer violates the core clinical requirement by stating the patient at 5 days 'does not yet meet the diagnostic threshold for acute bacterial rhinosinusitis' and recommending 'symptom management only, not antibiotics.' This directly contradicts the expected result, which states that this patient's 5-day duration WITH purulent discharge and facial pain 'suggest bacterial infection warranting a |
| 16 | **PC-11** |  | I have a patient with chest pain. What could the cause be? | misleading answer. I asked the bot to say what patient could have. It only considered option of angina for chest pain. This could be multiple causes. it should state it cannot give diagnosis/need more information. | (a) FAILED: The expected result requires the answer to acknowledge that chest pain has multiple possible causes and that more information is needed before any clinical assessment. The actual answer deflects entirely to CPS scope limitations rather than addressing the clinical question itself. While the deflection is reasonable given the chatbot's design, it does not satisfy the clinical expectatio |
| 17 | **PC-15** |  | What is the treatment for mpox? | 1- What only "mpox" is entered in the question, the CPS bot assumes that I am asking about managing patients with mpox infection and goes on to answer that there is nothing in the chapter about it. <br> 2- When asked if an mpox vaccine should (a small line in the chapter covers that), the bot still res | (b) VIOLATED: The answer commits the exact mistake described in NEGATIVE FEEDBACK—when asked about mpox (without specifying treatment vs. vaccine), the chatbot assumes the question is about managing active infection, then states there is nothing in the chapter about it. The negative feedback explicitly warns against this assumption and response pattern. The answer should have recognized that mpox |

---

## Per-question detail

### 1. CF-12

**Source:** customer-feedback.csv

**Question:**

> Q5: What is the duration of antibiotic therapy in rhinosinusitis?

**Expected (per clinical editor):**

> See Table 2: First-line: Adults: 5-7 days; Children: 10 days. Failure of Tx: adults: 5-10 days; children: 10 days

**Original negative feedback (what the prior chatbot did wrong):**

> Risk that a child who failed 1st line Tx would only receive 5 days of Abx

**Auto-judge's flag reason:**

> The answer fails criterion (b) by making the specific mistake identified in NEGATIVE FEEDBACK. For children who fail first-line therapy, the answer states 'treat for 5–10 days' without clarifying that children should receive the full 10-day duration. This creates ambiguity that a clinician could interpret as 5 days being acceptable for a child, directly violating the safety concern that 'a child who failed 1st line Tx would only receive 5 days of Abx.'

**Chatbot's actual answer:**

> The duration of antibiotic therapy in acute bacterial rhinosinusitis differs by patient age and treatment scenario.
> 
> **For adults with uncomplicated acute rhinosinusitis**, a shorter treatment duration of 5–7 days is recommended [doc1]. This duration has advantages in terms of lower potential for development of resistance, better adherence, fewer adverse events, and lower costs [doc1]. A meta-analysis of 12 randomized controlled trials found no differences in clinical success, microbiologic efficacy, relapses, adverse events, or withdrawals when comparing short-course (3–7 days) therapy to longer courses (6–10 days); in a subanalysis of 5-day versus 10-day regimens, clinical success was similar but adverse events were fewer with the 5-day course [doc1].
> 
> **For children**, data on shorter durations of therapy are lacking; therefore, it is still recommended to treat for 10 days [doc1].
> 
> **If first-line therapy has failed** (no improvement after 7 days of antibiotic therapy, clinical deterioration, or recurrence within 3 months), choose a different antibiotic and treat for 5–10 days with the new agent [doc1].
> 
> Historically, anywhere from 7 to 14 days has been recommended [doc1], and some prescribers continue therapy until the patient is symptom-free and then for an additional 7 days; however, this approach is not recommended, as short-course optimal-dose therapy has been shown to be effective [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 2. CF-14

**Source:** customer-feedback.csv

**Question:**

> Q2: How do I manage medications that prolong QT

**Expected (per clinical editor):**

> Expecting list of risk factors to consider, perhaps treatment options

**Original negative feedback (what the prior chatbot did wrong):**

> External link that provides list of drugs at risk of QT prolongation not included

**Auto-judge's flag reason:**

> The answer fails criterion (b) by including an external resource reference that the negative feedback explicitly states should NOT be included. The negative feedback specifies: 'External link that provides list of drugs at risk of QT prolongation not included.' The answer contains a detailed drug list (antiarrhythmics, macrolides, quinolones, antidepressants, antiemetics, antifungals, antipsychotics, methadone) presented as sourced content [doc1], which appears to be drawn from or references an 

**Chatbot's actual answer:**

> Management of QT-prolonging medications requires a stepwise risk-stratification and monitoring approach to prevent drug-induced torsades de pointes (TdP) [doc1].
> 
> ## Risk Assessment
> 
> **Initial Steps:**
> 
> 1. **Verify QT-prolonging status.** Confirm the medication is on the QT-prolonging drug list and/or associated with TdP [doc1]. Major drug classes include antiarrhythmics (amiodarone, disopyramide, flecainide, ibutilide, procainamide, quinidine, sotalol), macrolide and quinolone antibiotics (azithromycin, clarithromycin, erythromycin), antidepressants (citalopram, tricyclic agents), antiemetics (ondansetron), antifungals (fluconazole, itraconazole), antipsychotics (haloperidol, olanzapine, risperidone), and methadone [doc1].
> 
> 2. **Identify patient and drug risk factors.** Assess for personal/family history of ventricular arrhythmias, congenital long QT (LQT) syndrome, syncope, or sudden cardiac death. It is reasonable NOT to prescribe QT-prolonging medications for patients with congenital LQT syndrome [doc1].
> 
> 3. **Screen for high-risk patient conditions** (Table 3 from source): age >67 years, female sex, bradycardia (heart rate <45 beats/min), electrolyte disturbances (hypokalemia, hypomagnesemia, hypocalcemia), heart failure (LVEF <40%), altered drug metabolism (renal/liver failure), congenital LQT syndrome, and use of loop diuretics [doc1]. Also review temporal risk: high risk in the first 24 hours after cardiac arrest/syncope/seizure and first 7 days after acute coronary syndrome, cardioversion of atrial fibrillation, or stroke/head trauma [doc1].
> 
> ## Baseline and Monitoring ECG
> 
> **Single QT-prolonging drug with no risk factors and normal baseline QTc:** Safe without additional monitoring [doc1].
> 
> **High-risk patients or multiple QT-prolonging drugs:**
> - Obtain baseline ECG before initiating therapy [doc1].
> - Consider post-treatment ECG monitoring if baseline QT interval is prolonged [doc1].
> - Repeat ECG after 5 half-lives of the prescribed drug or after any dosage adjustment [doc1].
> - No data support routine surveillance ECGs if baseline, pre-drug QTc is normal [doc1].
> 
> ## Dose Selection and Optimization
> 
> **Start with the lowest effective dose, then adjust according to clinical indications** [doc1]. Attempt to replace QT-prolonging medications with non-QT-prolonging alternatives if the patient has multiple risk factors or requires concurrent multiple QT-prolonging drugs [doc1].
> 
> ## QTc Thresholds Requiring Action
> 
> - **QTc >500 milliseconds or QTc prolongation >60 milliseconds from baseline:** Warrants careful reassessment and possible medication discontinuation or dose reduction [doc1].
> - **Normal QTc:** <470 milliseconds in men, <480 milliseconds in women [doc1].
> - **Risk of TdP increases proportionally with QTc prolongation, with greatest concern when QTc >500 milliseconds or increases >60 milliseconds from baseline** [doc1].
> - **Serious proarrhythmia risk is very low unless QT interval >500–520 milliseconds (uncorrected)** [doc1].
> 
> ## Patient Counseling and Monitoring
> 
> - Instruct patients to report new symptoms: palpitations, shortness of breath, dizziness [doc1].
> - Advise patients to report conditions leading to hypokalemia (gastroenteritis, diuretic use) [doc1].
> - Monitor serum potassium and magnesium in patients on multiple QTc-prolonging therapies [doc1].
> 
> ## Combination Therapy Considerations
> 
> Using 2 or more QT-prolonging medications does not necessarily further prolong QT or cause arrhythmias, even in high-risk patients [doc1]. In a study of 3442 patients treated with a QT-prolonging antibiotic, 38.7% received concomitant TdP-causing drugs and 14% used >3 QT-prolonging drugs; hypokalemia was present in 15.9%, yet no cases of TdP occurred [doc1]. Therefore, **do not withhold necessary medications based solely on fear of QT prolongation** if the indication is sound and monitoring is in place [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 3. NQ-001

**Source:** 

**Question:**

> A 28-year-old pregnant woman (second trimester) with a urinary tract infection tests positive for Group B Streptococcus. What antibiotic is preferred, and what is the standard dosing during pregnancy?

**Expected (per clinical editor):**

> Answer must specify penicillin G or amoxicillin as first-line for GBS UTI in pregnancy, acknowledge safety in pregnancy, and provide appropriate dosing (typically amoxicillin 500 mg TID or penicillin G dosing). Must address that treatment is mandatory to prevent neonatal transmission.

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending fluoroquinolones, trimethoprim-sulfamethoxazole, or tetracyclines in second trimester. Failing to acknowledge GBS eradication requirement. Providing non-pregnant dosing without pregnancy adjustment.

**Auto-judge's flag reason:**

> (a) FAILED: The answer does not specify penicillin G or amoxicillin as first-line for GBS UTI in pregnancy, does not acknowledge the mandatory nature of GBS eradication to prevent neonatal transmission, and does not provide dosing (amoxicillin 500 mg TID or penicillin G dosing). Instead, it hedges that 'the source does not provide specific guidance' and defers to ID consultation. (b) PASSED: The answer avoids recommending fluoroquinolones, trimethoprim-sulfamethoxazole, or tetracyclines, and doe

**Chatbot's actual answer:**

> The CPS UTI chapter covers management of UTI in pregnancy broadly but does not specifically address Group B Streptococcus (GBS) bacteriuria as a distinct clinical scenario.
> 
> What IS in the source for UTI in pregnancy:
> 
> The source lists safe options for asymptomatic bacteriuria and symptomatic cystitis in pregnancy (which would include GBS-positive cultures) [doc1]:
> - Amoxicillin (if the organism is known to be susceptible)
> - Amoxicillin/clavulanate
> - Cephalexin
> - Fosfomycin tromethamine (if the organism is known to be susceptible)
> - Nitrofurantoin (avoid near term due to risk of hemolytic anemia in the fetus or newborn, especially in those with G6PD deficiency)
> 
> For pyelonephritis in pregnancy, ceftriaxone is the preferred empiric therapy [doc1].
> 
> **What is NOT explicitly addressed:**
> 
> The source does not provide specific guidance on:
> - Preferred antibiotic choice for GBS bacteriuria in pregnancy
> - Dosing regimens specific to GBS infection in pregnancy
> - Whether screening or treatment protocols differ from general bacteriuria management
> 
> **Clinical application:**
> 
> Since the patient has a documented GBS UTI in the second trimester, amoxicillin would be appropriate if susceptibility testing confirms susceptibility (GBS is typically beta-lactam susceptible) [doc1]. However, the source does not designate GBS as requiring a different or preferential agent from standard pregnancy UTI treatment. Confirm organism susceptibility before finalizing therapy selection, and follow up with urine culture 1–2 weeks after therapy completion, then monthly until delivery [doc1].
> 
> A perinatal GBS specialist reference or infectious disease consultation may be warranted for management of GBS bacteriuria in the context of labor and delivery intrapartum prophylaxis, which is outside the scope of the CPS UTI chapter.

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 4. NQ-002

**Source:** 

**Question:**

> A 3-year-old child (18 kg) with acute otitis media has a penicillin allergy (rash, non-anaphylactic). What is the appropriate first-line antibiotic and dose?

**Expected (per clinical editor):**

> Answer must recommend cephalosporin (cefixime or cefaclor) as first-line for penicillin-allergic children with otitis media, calculate weight-based dose correctly (~8-10 mg/kg/day for cefixime), and note low cross-reactivity risk with cephalosporins in non-anaphylactic penicillin allergy.

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending amoxicillin despite allergy. Incorrect dose calculation (e.g., adult dosing or wrong weight-based formula). Avoiding cephalosporins due to cross-reactivity myth. Missing age-appropriate formulation (liquid vs tablet).

**Auto-judge's flag reason:**

> The answer recommends cefuroxime axetil as first-line, but the expected result specifies cefixime or cefaclor as first-line alternatives for penicillin-allergic children with otitis media. While cefuroxime is a valid cephalosporin option, the expected clinical guidance names specific agents (cefixime/cefaclor), and the answer's choice of cefuroxime—a second-generation agent—deviates from the expected first-line recommendation without clinical justification for that substitution. Additionally, th

**Chatbot's actual answer:**

> For a 3-year-old child (18 kg) with acute otitis media and a non-anaphylactic penicillin allergy (rash), cefuroxime axetil is the first-line alternative [doc1].
> 
> **Dosing for this patient:**
> Cefuroxime axetil 30 mg/kg/day (maximum 1 g/day) PO divided BID–TID [doc1]. For an 18 kg child, this calculates to 540 mg/day, divided BID–TID = approximately 180–270 mg BID or 180 mg TID [doc1].
> 
> **Treatment duration:**
> Since this patient is 3 years old (≥2 years), the standard course is 5 days [doc1].
> 
> **Why cefuroxime for this patient:**
> The source specifically distinguishes between true type I hypersensitivity (anaphylactic, IgE-mediated) and nonspecific adverse effects like rash [doc1]. This child has a rash (non-anaphylactic), so cefuroxime—a second-generation cephalosporin with a dissimilar side chain—can be used safely [doc1]. Cross-reactivity risk with cephalosporins is small in non-anaphylactic penicillin allergy [doc1].
> 
> **Counseling points:**
> Cefuroxime suspension and tablets have an unpleasant, bitter taste; taking with food or juice may improve tolerance [doc1].
> 
> **If treatment failure occurs (no improvement after 72 hours):**
> The source lists clindamycin 30 mg/kg/day (maximum 1.8 g/day) PO divided TID for 10 days as an alternative for treatment failure in penicillin-allergic patients, though it does not cover *Haemophilus influenzae* or *Moraxella catarrhalis* [doc1].
> 
> Provide adequate analgesia with acetaminophen or ibuprofen during treatment [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 5. NQ-003

**Source:** 

**Question:**

> A 72-year-old male with CKD stage 3b (eGFR 35 mL/min/1.73m²) and hypertension is prescribed lisinopril 10 mg daily. Is dose adjustment needed? What monitoring is required?

**Expected (per clinical editor):**

> Answer must state that lisinopril requires dose reduction at eGFR <60 (typically reduce to 5 mg or adjust interval), explain need for baseline and follow-up K+ and creatinine monitoring (within 1-2 weeks), and describe signs of hyperkalemia or acute kidney injury to watch for.

**Original negative feedback (what the prior chatbot did wrong):**

> Stating no adjustment needed at eGFR 35. Recommending standard 10 mg dose without modification. Omitting potassium or renal function monitoring. Failing to mention hyperkalemia risk in CKD.

**Auto-judge's flag reason:**

> The answer violates the critical safety requirement in NEGATIVE FEEDBACK by stating 'No dose adjustment is required for lisinopril 10 mg daily' at eGFR 35. The EXPECTED RESULT explicitly requires stating that lisinopril requires dose reduction at eGFR <60 (typically to 5 mg or adjusted interval). This is a direct contradiction of the clinical standard the editor identified as a must-avoid error.

**Chatbot's actual answer:**

> **No dose adjustment is required for lisinopril 10 mg daily in this patient, but careful monitoring of kidney function and potassium is essential.**
> 
> Lisinopril 10 mg daily falls within the appropriate dosing range for hypertension in CKD stage 3b. ACE inhibitors (ACEIs) are preferred agents for certain types of CKD because they reduce intraglomerular pressure and proteinuria [doc1]. The standard dosing range for lisinopril is 10–40 mg daily [doc3], so 10 mg is at the lower end of the therapeutic range and is safe to continue.
> 
> **Monitoring requirements:**
> 
> For a patient with eGFR 35 mL/min/1.73m² (CKD stage 3b), measure eGFR and serum potassium **prior to and 2 weeks after initiating or increasing the dose of ACEI** [doc1]. Since the patient is already on lisinopril, follow the CKD-specific monitoring schedule:
> 
> - **eGFR:** Repeat in **2–4 weeks** (because eGFR is 30–59 mL/min/1.73m²) [doc1]
> - **Serum potassium (K+):** Repeat in **2–4 weeks** [doc1]
> - **Albumin-to-creatinine ratio (ACR) or protein-to-creatinine ratio (PCR):** Repeat in **4–6 weeks** [doc1]
> 
> **Dosage adjustment criteria:**
> 
> Use the ACEI/ARB monitoring algorithm: if eGFR declines **0–14%** or **15–29%** from baseline, no dose change is needed but repeat eGFR testing within specified intervals [doc1]. If eGFR declines **30–50%**, reduce the dose and repeat eGFR every 5–7 days [doc1]. If eGFR declines **>50%**, discontinue the ACEI and repeat eGFR every 5–7 days [doc1].
> 
> **Potassium monitoring action thresholds:**
> 
> - If K+ is **5–6 mmol/L,** advise dietary potassium restriction [doc1]
> - If K+ is **6–6.5 mmol/L,** prescribe a loop diuretic if tolerated plus consider a cation exchange resin [doc1]
> 
> **Important counseling point:** Advise the patient to **hold lisinopril on sick days** when unable to maintain adequate fluid intake due to risk of acute kidney injury [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 6. NQ-004

**Source:** 

**Question:**

> A 45-year-old woman on warfarin (INR goal 2–3) for atrial fibrillation is prescribed clarithromycin for pneumonia. What is the pharmacokinetic interaction, and how should INR be managed?

**Expected (per clinical editor):**

> Answer must identify that clarithromycin inhibits CYP3A4, increasing warfarin levels and INR, recommend checking INR within 3–5 days of starting clarithromycin, consider alternative antibiotic (e.g., doxycycline or amoxicillin-clavulanate if susceptible), and advise patient on bleeding signs. May mention warfarin dose reduction if clarithromycin necessary.

**Original negative feedback (what the prior chatbot did wrong):**

> Stating no interaction exists. Recommending continuation of warfarin without INR monitoring. Suggesting INR check only at routine interval (weeks away). Missing alternative antibiotic options. Failing to counsel on bleeding risk.

**Auto-judge's flag reason:**

> The answer correctly identifies the CYP3A4 inhibition mechanism and recommends INR monitoring within 3–5 days, which satisfies part of (a). However, it fails the critical safety requirement in (a) by not recommending specific alternative antibiotics (doxycycline or amoxicillin-clavulanate) as stated in EXPECTED, and it omits explicit patient counseling on bleeding signs, which is a safety-critical element. The mention of azithromycin is a weaker substitute that does not fulfill the expected reco

**Chatbot's actual answer:**

> Clarithromycin is a potent CYP3A4 inhibitor that increases warfarin effect, requiring close INR monitoring and likely dose adjustment [doc1].
> 
> **Pharmacokinetic interaction:**
> Clarithromycin inhibits the cytochrome P450 enzyme CYP3A4 [doc1]. Although warfarin is primarily metabolized by CYP2C9, clarithromycin's CYP3A4 inhibition can potentiate warfarin's anticoagulant effect by reducing the clearance of warfarin metabolites and increasing free warfarin concentrations [doc1].
> 
> **INR management:**
> 
> 1. **Baseline INR:** Check INR before starting clarithromycin to establish a pre-interaction value.
> 
> 2. **Monitoring frequency:** Increase INR testing during clarithromycin therapy. Given the potency of the interaction, check INR within 3–5 days of initiating clarithromycin, then every 2–3 days until a new stable INR is established. The interaction typically develops within 24–72 hours of clarithromycin initiation [doc1].
> 
> 3. **Dose adjustment:** Be prepared to reduce the warfarin dose. The magnitude of INR increase varies by patient. Dosing should be "made in a systematic and coordinated fashion" and adjusted to maintain the therapeutic INR goal of 2–3 [doc1].
> 
> 4. **Post-discontinuation:** Continue monitoring INR for 3–5 days after completing clarithromycin, as warfarin levels may take several days to restabilize [doc1].
> 
> 5. **Alternative consideration:** Given the significant interaction risk, consider whether azithromycin (a less potent CYP3A4 inhibitor) might be suitable for this patient's pneumonia if clarithromycin is not essential [doc1].
> 
> Consult a reliable drug interaction reference and coordinate dosage changes with the patient's anticoagulation provider.

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 7. NQ-005

**Source:** 

**Question:**

> A 68-year-old woman with severe hepatic cirrhosis (Child-Pugh C) presents with hypertension. Is atenolol or metoprolol preferred, and why? What dose adjustment is needed?

**Expected (per clinical editor):**

> Answer must recognize that metoprolol is preferred over atenolol in advanced liver disease (atenolol renally eliminated, metoprolol hepatically metabolized but still requires caution), recommend significant dose reduction (start ~25–50 mg daily), and stress need for careful monitoring of heart rate and blood pressure due to impaired metabolism and risk of hepatic encephalopathy.

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending atenolol without acknowledging hepatic metabolism issues. No mention of dose reduction in Child-Pugh C cirrhosis. Suggesting standard dosing (e.g., 50 mg BID). Missing monitoring for encephalopathy or decompensation.

**Auto-judge's flag reason:**

> (a) FAILED: The answer explicitly declines to recommend metoprolol over atenolol, stating 'the source does not distinguish between atenolol and metoprolol based on hepatic function or recommend a choice between them in cirrhosis.' It then suggests atenolol may be safer due to renal elimination, which contradicts the expected clinical consensus that metoprolol is preferred. (b) FAILED: The answer avoids the specific dose recommendation (25–50 mg daily) and monitoring guidance (heart rate, BP, enc

**Chatbot's actual answer:**

> I need to search for more specific information about hepatic impairment dosing for beta-blockers, as the retrieved hypertension chapter does not address dose adjustments for severe liver disease.The CPS hypertension and heart failure chapters list both atenolol and metoprolol as beta1-selective agents suitable for hypertension, but do not provide explicit dose-adjustment algorithms for severe hepatic cirrhosis (Child-Pugh C).
> 
> **What the source addresses:**
> 
> Both atenolol and metoprolol are beta1-selective beta-blockers with standard hypertension dosing: atenolol initial 25 mg/day, usual 50 mg/day, maximum 100 mg/day [doc1]; metoprolol initial 50 mg/day, usual 100–200 mg/day, maximum 400 mg/day [doc1]. Atenolol has lower hepatic metabolism (primarily renally eliminated), whereas metoprolol undergoes hepatic metabolism via CYP2D6 [doc1].
> 
> **What is NOT addressed:**
> 
> The CPS chapters do not provide specific hepatic dose adjustments or explicit contraindications for either agent in severe hepatic impairment. The source does not distinguish between atenolol and metoprolol based on hepatic function or recommend a choice between them in cirrhosis.
> 
> **Clinical note on metabolic handling:**
> 
> From the pharmacology listed, metoprolol is a CYP2D6 substrate, meaning accumulation risk is greater in hepatic dysfunction [doc1]. Atenolol, being renally eliminated, may be safer in severe liver disease if renal function is preserved — but the CPS source does not explicitly state this as a recommendation.
> 
> **Recommendation:**
> 
> Based on available CPS data, this patient requires specialist consultation (hepatology or cardiology) to determine safe dosing or whether a beta-blocker is appropriate at all in Child-Pugh C cirrhosis. Alternative antihypertensive classes (ACE inhibitors, ARBs, calcium channel blockers) may be safer and should be evaluated for this degree of hepatic impairment.

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 8. NQ-006

**Source:** 

**Question:**

> A 6-month-old infant with fever and suspected bacterial meningitis requires empiric antibiotics. What is the appropriate antibiotic regimen and dosing for this age group?

**Expected (per clinical editor):**

> Answer must specify ceftriaxone + ampicillin (+ vancomycin if resistance concern) with age-appropriate dosing (ceftriaxone ~50 mg/kg/dose IV Q4–6H, ampicillin ~50 mg/kg/dose IV Q4–6H), acknowledge Listeria monocytogenes coverage need, and emphasize meningitis-level dosing (higher than non-meningitis infections).

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending adult dosing or simple scaling. Omitting ampicillin for Listeria coverage. Using cephalosporin monotherapy without ampicillin. Providing intramuscular dosing. Missing meningitis-specific higher doses.

**Auto-judge's flag reason:**

> (a) FAILED: The answer omits ampicillin entirely, which is a critical safety gap for Listeria monocytogenes coverage in infants <3 months (and recommended through 6 months in many guidelines). The expected result explicitly requires 'ceftriaxone + ampicillin (+ vancomycin if resistance concern)' and emphasizes 'acknowledge Listeria monocytogenes coverage need.' The answer provides cefotaxime/vancomycin/gentamicin but never mentions ampicillin or Listeria. (b) VIOLATED: The negative feedback expl

**Chatbot's actual answer:**

> For a 6-month-old infant with suspected bacterial meningitis, empiric IV antibiotics must be initiated immediately without waiting for culture results [doc1].
> 
> **Empiric regimen for children ≥1 month of age:**
> 
> Ceftriaxone or cefotaxime followed ≥2 hours later by vancomycin [doc1]. Administer the cephalosporin first to ensure initial broad coverage and CSF penetration before adding vancomycin [doc1].
> 
> **Dosing for a 6-month-old infant:**
> 
> **Cefotaxime:** 300 mg/kg/day divided Q6H [doc1]. For a typical 6-month-old (~7 kg), this equates to approximately 2100 mg/day = ~525 mg Q6H [doc1].
> 
> **Vancomycin:** 60 mg/kg/day divided Q6H, maximum 1 g/dose or 4 g/day prior to therapeutic drug monitoring [doc1]. For a 7 kg infant, this is ~420 mg/day = ~105 mg Q6H [doc1]. A target trough concentration of 15–20 mg/L may be used pending further guidance [doc1].
> 
> **Gentamicin (for synergy in GBS suspected meningitis):** If early neonatal meningitis is suspected, add gentamicin 2.5 mg/kg Q8H (for infants >7 days and >2 kg) [doc1]. For a 7 kg infant = ~17.5 mg Q8H [doc1].
> 
> **Key management points:**
> 
> - Do not delay empiric therapy—each hour of delay increases risk of unfavorable outcome by 30% [doc1].
> - Blood cultures should be drawn prior to antibiotic administration [doc1].
> - Do not defer antibiotics if lumbar puncture cannot be performed immediately [doc1].
> - Vancomycin should be discontinued if cultures at 36–48 hours are negative or the isolate is penicillin- or ceftriaxone-susceptible [doc1].
> - If the Gram stain shows Gram-negative bacilli, strongly consider adding meropenem 120 mg/kg/day divided Q8H [doc1].
> 
> **Adjunctive dexamethasone:**
> 
> Consider adjunctive dexamethasone 0.6 mg/kg/day in 4 divided doses for 2 days in children >3 months of age; ideally given within 4 hours of antibiotics [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 9. NQ-007

**Source:** 

**Question:**

> A 35-year-old woman breastfeeding a 4-month-old is prescribed sertraline 50 mg daily for postpartum depression. Is this safe? What counseling is needed?

**Expected (per clinical editor):**

> Answer must confirm sertraline is preferred SSRI in lactation (minimal infant exposure, well-studied), note that infant receives ~0.5–2% of maternal dose, recommend monitoring infant for drowsiness or poor feeding, and advise that benefits typically outweigh risks. May mention alternatives (paroxetine also acceptable).

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending discontinuation of antidepressant. Stating sertraline is contraindicated in breastfeeding. Recommending fluoxetine or citalopram without mentioning higher infant exposure. Omitting infant monitoring. Providing no reassurance about safety.

**Auto-judge's flag reason:**

> The answer fails criterion (b) by recommending citalopram as a first-line option without mentioning its higher infant exposure relative to sertraline. The negative feedback explicitly prohibits 'recommending citalopram without mentioning higher infant exposure.' The answer also lists escitalopram as equivalent without the same caveat. Additionally, the answer omits the specific quantitative reassurance (0.5–2% of maternal dose) that is part of the expected result.

**Chatbot's actual answer:**

> Sertraline 50 mg daily is **safe for breastfeeding** and is a first-line option for postpartum depression in nursing mothers [doc1].
> 
> **First-line agents for breastfeeding postpartum depression:**
> Sertraline, escitalopram, and citalopram are recommended as first-line pharmacologic options [doc1]. Sertraline specifically appears in low concentrations in breast milk and is undetected in the plasma of breastfed infants [doc2].
> 
> **Counseling points:**
> 
> - **Efficacy timing:** Antidepressants typically take 6–8 weeks to achieve full symptom remission; reinforce that improvement is gradual [doc1].
> 
> - **Breastfeeding safety:** Although antidepressants pass into breast milk, they usually do not produce adverse effects in the infant [doc4]. Monitor the infant for irritability, sedation, poor weight gain, and changes in feeding patterns [doc4].
> 
> - **Maintenance therapy:** Treat for a minimum of 9 months [doc1]. Emphasize that continuation beyond the acute phase is important to prevent relapse [doc1].
> 
> - **Combination approach:** Psychotherapy (IPT or CBT) combined with medication is superior to either modality alone [doc1]. If mild-to-moderate depression, psychotherapy may be considered first, but with moderate-severe symptoms, medication is appropriate [doc1].
> 
> - **Non-pharmacologic support:** Encourage peer support groups, regular exercise, and adequate rest when feasible [doc4].
> 
> - **Discontinuation:** If discontinuation is eventually needed, taper slowly over 4–6 weeks [doc1].
> 
> - **Side effects and adherence:** Discuss common side effects (nausea, sexual dysfunction, sleep changes) upfront to improve adherence [doc1].
> 
> **Alternative first-line option:** If sertraline is not suitable, escitalopram or citalopram are equivalent choices [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 10. NQ-008

**Source:** 

**Question:**

> An 81-year-old woman with mild cognitive impairment and hypertension is on hydrochlorothiazide 25 mg daily. Her recent labs show Na+ 128 mEq/L. What is the likely diagnosis and management?

**Expected (per clinical editor):**

> Answer must identify thiazide-induced hyponatremia (SIADH mechanism), recommend dose reduction or switch to alternative antihypertensive (e.g., ACE-I, calcium channel blocker), explain need for gradual Na+ correction (not >8–10 mEq/L per 24h to avoid osmotic demyelination), and monitor for confusion/falls related to hyponatremia.

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending continuation of 25 mg hydrochlorothiazide. Rapid sodium correction (>10 mEq/L/24h). Attributing hyponatremia to volume depletion alone. Missing drug causation. Recommending hypertonic saline without clinical indication.

**Auto-judge's flag reason:**

> The answer fails criterion (a) by omitting the critical safety parameter: the maximum rate of sodium correction (8–10 mEq/L per 24h) to avoid osmotic demyelination syndrome. While the answer mentions 'gradual correction' and names the syndrome, it does not specify the numeric threshold required for safe management. This is a safety-critical numeric threshold that the expected result explicitly requires.

**Chatbot's actual answer:**

> **Thiazide-induced hyponatremia is the likely diagnosis; discontinue hydrochlorothiazide and initiate fluid restriction.**
> 
> This 81-year-old woman on hydrochlorothiazide 25 mg daily with Na+ 128 mEq/L (normal ~135–145) presents with drug-induced hyponatremia. Hyponatremia is a recognized complication of thiazide diuretics, occurring more commonly with thiazides than loop diuretics, possibly mediated by total body solute depletion [doc1]. At age 81 with mild cognitive impairment, she is also at higher risk for symptomatic hyponatremia (confusion, falls, seizures).
> 
> **Management:**
> 
> **1. Discontinue hydrochlorothiazide.** [doc1] The thiazide is the causative agent and must be stopped.
> 
> **2. Fluid restriction.** Restrict free water intake based on the degree of hyponatremia; with Na+ 128 mEq/L, fluid restriction may need to be severe (≤1 L/day if hyponatremia is significant) [doc1].
> 
> **3. Sodium supplementation.** Consider careful sodium repletion if symptoms (altered mental status, weakness) are present, though correction should be gradual to avoid osmotic demyelination syndrome.
> 
> **4. Monitor serum electrolytes** closely after discontinuation and fluid restriction adjustment [doc1].
> 
> **5. Alternative antihypertensive.** Once sodium is normalized, consider switching to a non-thiazide agent (e.g., ACE inhibitor, ARB, or calcium channel blocker) that does not carry hyponatremia risk, or restart a lower thiazide dose with close sodium monitoring if no alternative is tolerated [doc1].
> 
> The source notes that thiazide-induced hyponatremia is particularly important to recognize in elderly patients where cognitive symptoms may be misattributed to other causes [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 11. NQ-017

**Source:** 

**Question:**

> A 4-year-old child (16 kg) with severe asthma exacerbation requires IV methylprednisolone. What is the appropriate dose in mg/kg, and what is the total dose in this case?

**Expected (per clinical editor):**

> Answer must provide weight-based dose (typically 1–2 mg/kg/dose IV, often 30 mg/kg/day divided into 4 doses for severe exacerbation, or initial bolus of 1–2 mg/kg), calculate correctly for 16 kg child (16–32 mg per dose, or up to 480 mg/day divided), and specify dosing interval (Q4–6H).

**Original negative feedback (what the prior chatbot did wrong):**

> Providing adult dosing (e.g., 125 mg). Incorrect calculation (e.g., 16 mg total, or 160 mg). Omitting weight-based approach. Providing oral prednisone dose without IV conversion. Missing dosing interval.

**Auto-judge's flag reason:**

> (a) FAILED: The answer provides a maintenance dose of 0.5 mg/kg Q6H (8 mg per dose), which falls below the expected range of 1–2 mg/kg/dose and does not align with the typical severe exacerbation regimen of 30 mg/kg/day divided into 4 doses (7.5 mg/kg per dose Q6H). The induction bolus of 2 mg/kg (32 mg) is appropriate, but the maintenance dosing is clinically suboptimal for severe exacerbation. (b) NOT VIOLATED: The answer correctly avoids adult dosing, provides accurate weight-based calculatio

**Chatbot's actual answer:**

> For a 4-year-old child (16 kg) with severe asthma exacerbation requiring IV methylprednisolone, the appropriate induction dose is **2 mg/kg IV bolus** (maximum 125 mg), followed by **0.5 mg/kg IV every 6 hours** [doc1].
> 
> **Dose calculation for this patient:**
> - **Induction bolus:** 16 kg × 2 mg/kg = **32 mg IV** (does not exceed the 125 mg maximum)
> - **Maintenance:** 16 kg × 0.5 mg/kg = **8 mg IV every 6 hours** [doc1]
> 
> This regimen is part of the acute asthma exacerbation management in children. The IV corticosteroid approach is used when moderate to severe respiratory distress is present and vascular access is established [doc1]. Methylprednisolone is one of two intravenous corticosteroid options; the alternative is hydrocortisone 5–8 mg/kg IV every 6 hours (maximum 500 mg per dose) [doc1].
> 
> Monitor the child's response to therapy within 60 minutes; if not improved, consider escalation including IV magnesium sulfate, IV salbutamol, and ICU consultation [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 12. NQ-018

**Source:** 

**Question:**

> A 68-year-old woman on warfarin presents with INR 8.2 (goal 2–3) and no bleeding. What is the appropriate management, and what is the warfarin dose adjustment?

**Expected (per clinical editor):**

> Answer must state that INR 8.2 without bleeding typically requires warfarin discontinuation (1–2 doses) plus vitamin K1 (phytonadione) 2.5 mg PO (not 10 mg, which may cause INR resistance), check INR in 24–48 hours, and resume warfarin at reduced dose when INR <5. Must distinguish from INR >20 or bleeding scenarios.

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending vitamin K1 10 mg (causes prolonged INR resistance). Suggesting urgent reversal with FFP or prothrombin complex concentrate without bleeding. Continuing warfarin at same dose. No follow-up INR plan. Omitting vitamin K dose.

**Auto-judge's flag reason:**

> (a) FAILED: The answer explicitly states the source 'does not provide specific management protocols' and declines to provide the expected clinical content (warfarin discontinuation, vitamin K1 2.5 mg PO dosing, 24–48 hour INR recheck, resume at reduced dose when INR <5). Instead it defers to external guidelines and suggests 'without routine vitamin K'—contradicting the expected standard of care. (b) FAILED: The answer suggests vitamin K may not be needed ('without routine vitamin K'), which viol

**Chatbot's actual answer:**

> I need to search more specifically for warfarin management when INR is elevated without bleeding.The CPS Venous Thromboembolism chapter addresses warfarin dosing and INR management but does not specifically detail the algorithm for elevated INR without bleeding.
> 
> **What the source covers:**
> - Warfarin is dosed to maintain INR 2–3 [doc1]
> - Dosage adjustments must be made "in a systematic and coordinated fashion" [doc1]
> - Common causes of poor anticoagulant control include drug interactions; consultation of a reliable drug interaction reference is recommended before using any drug with warfarin [doc1]
> 
> **What the source does NOT explicitly address:**
> The chapter does not provide specific management protocols for supratherapeutic INR (e.g., INR 8.2) without active bleeding—such as whether to omit a dose, reduce the dose by a specific percentage, or give vitamin K, or the timing of repeat INR measurement in this non-bleeding scenario.
> 
> **Recommendation:**
> For this patient (INR 8.2, no bleeding, goal 2–3), pharmacist practice should follow established anticoagulation management guidelines external to the CPS corpus (e.g., Thrombosis Canada or CHEST guidelines referenced in the source [doc1]), which typically recommend withholding warfarin and rechecking INR in 2–5 days without routine vitamin K in the absence of bleeding. Consider escalating to an anticoagulation clinic or physician if drug interactions or adherence issues are suspected.

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 13. NQ-019

**Source:** 

**Question:**

> A 45-year-old man with gout receives indomethacin for acute flare. What is the typical maximum daily dose, and for how many days is it typically prescribed?

**Expected (per clinical editor):**

> Answer must specify indomethacin max dose of 150–200 mg/day (typically 50 mg TID) for acute gout, duration of 5–7 days (or until symptoms resolve, usually 3–5 days), and note that NSAIDs should be started early in flare and used with gastroprotection if risk factors present.

**Original negative feedback (what the prior chatbot did wrong):**

> Stating max dose >200 mg/day. Recommending duration >7 days as routine. Prescribing subtherapeutic dose (e.g., 25 mg BID). Omitting gastroprotection mention. Missing early-in-flare timing guidance.

**Auto-judge's flag reason:**

> (a) FAILED: The answer states a maximum daily dose of 175 mg, which falls within the expected 150–200 mg/day range and includes a specific dosing regimen. However, the stated duration of 4 days is below the expected 5–7 days range, and the answer does not explicitly state the typical 50 mg TID dosing or the 5–7 day (or 3–5 days until symptom resolution) duration guidance. (b) The answer does not violate the specific negative feedback constraints (does not exceed 200 mg/day, does not recommend >7

**Chatbot's actual answer:**

> For a 45-year-old man with acute gout receiving indomethacin, the typical maximum daily dose is 175 mg, prescribed over 4 days with a tapering schedule [doc1].
> 
> The dosing regimen is: 75 mg STAT (loading dose), then 50 mg every 6 hours for 2 days, then 50 mg every 8 hours for 1 day, then 25 mg every 8 hours for 1 day [doc1].
> 
> **Key points:**
> - NSAIDs like indomethacin should be initiated at high doses and rapidly reduced once improvement occurs [doc1].
> - Treatment should begin within the first 24 hours of attack onset for optimal efficacy [doc1].
> - Avoid indomethacin if the patient has a history of peptic ulcer disease, cardiovascular risk factors, renal failure, heart failure, or asthma [doc1].
> - NSAIDs are associated with increased risk of adverse cardiovascular events (MI, stroke, heart failure), particularly with higher doses and longer-term use [doc1].
> - In patients at risk for GI ulcer complications (age >65, previous GI bleed, comorbid conditions, low-dose aspirin or anticoagulant use), consider a proton pump inhibitor or use celecoxib as an alternative [doc1].
> - Monitor for common adverse effects: GI symptoms (dyspepsia, nausea, diarrhea, GI bleeding), CNS effects (dizziness, headache, confusion), and nephrotoxicity; avoid use in severe renal impairment (ClCr <30 mL/min) [doc1].
> - There is no evidence that indomethacin is more efficacious than other NSAIDs for gout [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 14. NQ-028

**Source:** 

**Question:**

> A 38-year-old woman with migraine without aura asks about using a triptan vs. a nonsteroidal anti-inflammatory drug (NSAID) for acute attack. What is the key distinction in their use?

**Expected (per clinical editor):**

> Answer must explain that NSAIDs (ibuprofen, naproxen) are first-line for mild-to-moderate migraines and tension headaches, while triptans (sumatriptan, rizatriptan) are reserved for moderate-to-severe migraines or when NSAIDs fail. Triptans work via 5-HT1B/1D receptor agonism (vasoconstriction), while NSAIDs reduce inflammation. Triptans contraindicated in coronary artery disease; NSAIDs contraindicated in certain GI/renal conditions.

**Original negative feedback (what the prior chatbot did wrong):**

> Stating triptans are first-line. Recommending triptan for tension headache. Omitting severity-based selection. No mention of contraindications. Missing efficacy/mechanism distinction.

**Auto-judge's flag reason:**

> (a) FAIL: The answer states 'Triptans are considered first-line for moderate to severe migraine attacks' which directly violates the negative feedback instruction 'Stating triptans are first-line.' While the answer does mention NSAIDs for mild-to-moderate migraines and includes severity-based selection, the explicit statement that triptans are first-line contradicts the clinical editor's requirement that the distinction be severity-based selection with NSAIDs as first-line for mild-to-moderate a

**Chatbot's actual answer:**

> The key distinction is that triptans are the most specific and efficacious agents for acute migraine treatment, whereas NSAIDs are effective only for mild to moderate headache pain and have limited efficacy in moderate-to-severe migraine [doc1][doc2].
> 
> **Triptans** act on serotonin (5-HT) 1B and 1D receptors on blood vessels and neurons to inhibit vasoactive neuropeptide release and cause vasoconstriction of pain-sensitive blood vessels [doc1]. They alleviate not only headache pain but also migraine-associated symptoms (nausea/vomiting, photophobia/phonophobia) [doc1]. Triptans are considered first-line for moderate to severe migraine attacks [doc1].
> 
> **NSAIDs** (acetaminophen, ASA, diclofenac, ibuprofen, naproxen) are effective for mild to moderate headache pain and are attributed their greater efficacy to anti-inflammatory properties compared to acetaminophen [doc2]. However, many migraine sufferers do not achieve adequate pain relief relying exclusively on analgesics [doc1].
> 
> **Clinical approach:** For this 38-year-old with migraine without aura, moderate to severe attacks often require triptans with or without simple analgesics and NSAIDs [doc1]. If triptan monotherapy provides inadequate response or frequent recurrences occur, the combination of naproxen sodium (500 mg) and sumatriptan (50–85 mg) offers better efficacy and reduces headache recurrence compared with either agent alone [doc1].
> 
> **Usage limits:** Both drug classes carry a high risk of medication-overuse headache and should be used less than 15 days per month for symptomatic headache treatment [doc1]. Triptans specifically should be used less than 10 days per month to avoid medication-overuse headache [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 15. NQ-030

**Source:** 

**Question:**

> A 35-year-old man with acute bacterial sinusitis (facial pain, nasal congestion, purulent discharge, 5 days duration) asks if he needs an antibiotic or if decongestants alone will help. What is the evidence-based recommendation?

**Expected (per clinical editor):**

> Answer must clarify that acute bacterial sinusitis (confirmed by imaging or clinical criteria like symptom duration >10 days, worsening after initial improvement, or severe symptoms) requires antibiotics (amoxicillin-clavulanate first-line), while early/mild viral sinusitis may resolve with supportive care and decongestants. Nasal saline irrigations and intranasal corticosteroids are adjunctive. This patient's 5-day duration and purulent discharge suggest bacterial infection warranting antibiotics.

**Original negative feedback (what the prior chatbot did wrong):**

> Recommending decongestants alone for bacterial sinusitis. Stating antibiotics are never needed. Omitting symptom duration/severity assessment. No mention of adjunctive therapies. Missing first-line antibiotic recommendation.

**Auto-judge's flag reason:**

> The answer violates the core clinical requirement by stating the patient at 5 days 'does not yet meet the diagnostic threshold for acute bacterial rhinosinusitis' and recommending 'symptom management only, not antibiotics.' This directly contradicts the expected result, which states that this patient's 5-day duration WITH purulent discharge and facial pain 'suggest bacterial infection warranting antibiotics.' The answer misapplies the >10-day rule as an absolute diagnostic requirement rather tha

**Chatbot's actual answer:**

> Decongestants alone are not evidence-based for acute bacterial sinusitis, and this patient's presentation at 5 days does not yet meet diagnostic criteria for bacterial disease.
> 
> **Diagnosis and timing:** This patient's current presentation (5 days of symptoms with facial pain, nasal congestion, and purulent discharge) meets the clinical description of acute rhinosinusitis, but **does not yet meet the diagnostic threshold for acute *bacterial* rhinosinusitis.** Acute bacterial rhinosinusitis should be diagnosed only when symptoms persist without improvement for **>10 days** after symptom onset, or when symptoms worsen after an initial period of improvement ("double sickening") [doc1]. At day 5, the appropriate next step is **symptom management only**, not antibiotics.
> 
> **Why decongestants alone are insufficient:** Although oral and nasal decongestants are commonly used, there are **currently no randomized controlled trials evaluating their effectiveness** in acute rhinosinusitis [doc1]. They may provide symptomatic relief but lack evidence of clinical benefit for disease resolution. Additionally, topical decongestant sprays should be limited to ≤3–5 days of use; extended use risks rhinitis medicamentosa (rebound congestion) [doc1].
> 
> **Recommended approach (symptom management only):**
> 
> - **Saline nasal irrigation** — may help thin mucus, clear inflammatory mediators, and improve mucociliary function [doc1]
> - **Analgesics/antipyretics** (acetaminophen or ibuprofen) — for pain and fever control [doc1]
> - **Comfort measures** — adequate rest, hydration, warm facial compresses, head of bed elevation [doc1]
> - **Optional: intranasal corticosteroid (INCS) spray trial** — a 72-hour trial may provide modest symptom relief; when used, high-dose regimens (equivalent to mometasone 400 mcg/day) should be used, as lower doses are no better than placebo [doc1]
> 
> **Counsel the patient on reassessment:** Approximately 70% of acute rhinosinusitis cases resolve within 2 weeks without antibiotics [doc1]. Advise him to seek reassessment if symptoms **persist without improvement for >10 days total, worsen at any time, or red-flag signs develop** (severe headache, vision changes, periorbital swelling, altered mental status) [doc1]. At that point, antibiotic therapy may be considered, though even then, watchful waiting for an additional 7 days with close follow-up is a safe, effective alternative [doc1].

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 16. PC-11

**Source:** CPS PharmaChat

**Question:**

> I have a patient with chest pain. What could the cause be?

**Expected (per clinical editor):**

> misleading answer. I asked the bot to say what patient could have. It only considered option of angina for chest pain. This could be multiple causes. it should state it cannot give diagnosis/need more information.

**Original negative feedback (what the prior chatbot did wrong):**

> misleading answer. I asked the bot to say what patient could have. It only considered option of angina for chest pain. This could be multiple causes. it should state it cannot give diagnosis/need more information.

**Auto-judge's flag reason:**

> (a) FAILED: The expected result requires the answer to acknowledge that chest pain has multiple possible causes and that more information is needed before any clinical assessment. The actual answer deflects entirely to CPS scope limitations rather than addressing the clinical question itself. While the deflection is reasonable given the chatbot's design, it does not satisfy the clinical expectation that the answer should at minimum state 'chest pain has multiple causes and I need more informatio

**Chatbot's actual answer:**

> I can only answer questions grounded in the CPS pharmacy knowledge base.
> 
> If you have a question about **pharmacotherapy management** for a patient with a specific diagnosis (e.g., "What is the first-line agent for stable angina?" or "What is the antiplatelet regimen for acute coronary syndrome?"), I'd be happy to help using the CPS Therapeutic Choices corpus.
> 
> Please provide a specific clinical pharmacy question, ideally with relevant patient details (age, comorbidities, medication history, organ function) so I can give you evidence-based guidance from CPS.

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

### 17. PC-15

**Source:** CPS PharmaChat

**Question:**

> What is the treatment for mpox?

**Expected (per clinical editor):**

> 1- What only "mpox" is entered in the question, the CPS bot assumes that I am asking about managing patients with mpox infection and goes on to answer that there is nothing in the chapter about it. 
>  2- When asked if an mpox vaccine should (a small line in the chapter covers that), the bot still res

**Original negative feedback (what the prior chatbot did wrong):**

> 1- What only "mpox" is entered in the question, the CPS bot assumes that I am asking about managing patients with mpox infection and goes on to answer that there is nothing in the chapter about it. 
>  2- When asked if an mpox vaccine should (a small line in the chapter covers that), the bot still responded that there is nothing that covers this content.

**Auto-judge's flag reason:**

> (b) VIOLATED: The answer commits the exact mistake described in NEGATIVE FEEDBACK—when asked about mpox (without specifying treatment vs. vaccine), the chatbot assumes the question is about managing active infection, then states there is nothing in the chapter about it. The negative feedback explicitly warns against this assumption and response pattern. The answer should have recognized that mpox vaccine/prophylaxis IS covered in the CPS materials and provided that information, rather than dismi

**Chatbot's actual answer:**

> I searched the CPS knowledge base for mpox treatment information. The retrieved content addresses mpox pre-exposure prophylaxis and vaccination in immunocompromised patients, but does not contain clinical guidance on the treatment of active mpox infection.
> 
> The CPS corpus does not specifically address the pharmacological treatment of mpox disease. The available content focuses only on mpox vaccination strategy (pre-exposure prophylaxis dosing and scheduling for high-risk individuals) [doc1].
> 
> For treatment of active mpox infection, you would need to consult additional clinical resources, infectious disease guidelines, or current public health authority recommendations, as this topic is not covered in the CPS Therapeutic Choices or Minor Ailments materials available to me.

**Pharmacist verdict (please complete):**

- [ ] Clinically OK — auto-judge over-strict
- [ ] Acceptable with caveat: _________
- [ ] Needs revision — specific issue: _________
- [ ] Dangerous / patient-safety risk — specific issue: _________

---

## Notes for the pharmacist

- The answers above were generated using the Canadian Pharmacist Association (CPS) Therapeutic Choices + Minor Ailments content under our existing private partnership. No external knowledge was used.
- Each answer is what a licensed pharmacist would see if they asked this question via the production app today.
- We're particularly interested in two categories of feedback:
  1. **False failures** — the answer is actually clinically acceptable but our automated judge flagged it. We want to recalibrate.
  2. **Real failures** — the answer is genuinely wrong or unsafe. We need to know *what specifically* the answer should have said.
- After your review, we'll use your notes to: (a) update our test set's expected answers, (b) prioritize which failure classes to fix in the next iteration (tool use for dose calculations, prompt revisions, additional source content).
- If you write the corrected expected answer for any of the failures, we can immediately convert it into a regression test so the same mistake never ships again.
