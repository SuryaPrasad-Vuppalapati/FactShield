Perfect. Here is the complete architecture document as a markdown file. You can copy this entire text and save it as `factshield_architecture.md` in your project root directory.

---

# FactShield Edu RAG - Complete Architectural Blueprint

**Version:** 1.0  
**Last Updated:** 2025  
**Target Platform:** MacBook Air M4, 16GB RAM  
**Target Market:** Grade 9 through PhD

---

## TABLE OF CONTENTS

1. [System Identity and Target Market](#part-1-system-identity-and-target-market)
2. [Source Document Types and Citation Rules](#part-2-source-document-types-and-citation-rules)
3. [Student Features](#part-3-student-features-grade-9-to-phd)
4. [Teacher Features](#part-4-teacher-features)
5. [Core Engine Architecture](#part-5-the-core-engine-architecture)
6. [Hardware Constraints](#part-6-hardware-constraints-and-configuration)
7. [Frontend UI Specifications](#part-7-frontend-ui-specifications)
8. [Absolute Rules](#part-8-absolute-rules-never-violate)
9. [Implementation Instructions](#part-9-your-instructions-critical---read-carefully)

---

## PART 1: SYSTEM IDENTITY AND TARGET MARKET

### Overview

FactShield is a strict, hallucination-proof Active Learning Assistant. Standard LLMs are designed to be "helpful at all costs," resulting in fabrications and generic answers. FactShield is designed to be "accurate at all costs." It forces grounding in verified sources, refuses to hallucinate, proves every claim through a 3-Pipeline validation system, and uses a Multi-Agent Orchestrator for verified online fallbacks only when necessary.

**CORE PRINCIPLE:**
Every answer, every response, every output from FactShield must be traceable to a verified source. If the system cannot ground a response, it refuses to provide one.

### Target Market

The system is exclusively optimized for **Grade 9 through PhD** (Secondary Education, Higher Education, and Research). 

The target user:
- Can read complex text
- Requires rigorous citation
- Understands source grounding
- Deals with dense, syllabus-specific material

**Note:** This system does NOT serve Grade 1 through 8. A separate product line would be required for that market.

---

## PART 2: SOURCE DOCUMENT TYPES AND CITATION RULES

### Universal Citation Law

FactShield handles two source types. The citation rules below are universal laws applying to every feature, every output, and every user role without exception.

### SOURCE TYPE A: PAGINATED FILES (Local Documents)

**Description:**  
Documents uploaded directly by the user.  
Examples: PDFs, Word documents, textbooks, syllabus files, lecture notes.

**Citation Rule:**  
Show page number or section reference only.

**Format Examples:**
- `[Page X]`
- `[Section: Name]`
- `[Page X, Section: Name]`

**Absolute Restrictions:**
- Never show a URL
- Never show a hyperlink
- Never use the word "Reference"
- Never indicate where the system found the content

**Rationale:**  
The user already possesses the file. Page numbers are sufficient for retrieval. URLs for local files are meaningless.

### SOURCE TYPE B: URL-BASED DOCUMENTS (Online Sources)

**Description:**  
Any document accessible via a URL.  
Examples: Web links provided by the user, ArXiv papers found by Orchestrator, Copilot knowledge base, live web results.

**Citation Rule:**  
Full URL hyperlink is strictly mandatory.

**Format:**  
`Reference: [Source Name](URL)`

**Examples:**
- `Reference: [Gradient Descent Explained](https://arxiv.org/...)`
- `Reference: [Machine Learning Basics](https://en.wikipedia.org/...)`
- `Reference: [Copilot AI Knowledge Base](https://copilot.microsoft.com/...)`

**Absolute Requirements:**
- URL must be clickable and functional
- Source name must be descriptive
- No citation = answer is invalid and must be rejected

**Rationale:**  
The user does not possess the document. A URL allows them to verify the source and read the original context themselves.

### UI BANNERS FOR SOURCE PROVENANCE

The system must always inform the user which source type was used. Banners are rendered based on whether a fallback occurred.

**Primary User-Provided Source (File or Link):**
- Banner: None. This is the expected, default source.
- Citation: Rendered per source type rule above.

**AI Fallback - ArXiv:**
- Banner: `Source: Academic Research (ArXiv)`
- Citation: `Reference: [Paper Title](URL)`

**AI Fallback - Copilot:**
- Banner: `Source: AI Knowledge Base (Copilot)`
- Citation: `Reference: [Copilot](URL)`

**AI Fallback - Web:**
- Banner: `Source: Live Web Search`
- Citation: `Reference: [Site Name](URL)`

**Strict Mode Refusal:**
- Banner: `FactShield Strict Mode Refusal`
- Citation: None

---

## PART 3: STUDENT FEATURES (GRADE 9 TO PHD)

All student features below MUST pass the 3-Pipeline Gatekeeper before any output is shown to the user.

---

### STUDENT FEATURE 1: CONCEPT GUIDE (Explanation + Verification)

#### Purpose

The student asks a complex question about their course material. The system retrieves relevant context and synthesizes a clear, comprehensive explanation grounded 100% in the uploaded document.

#### Functionality

1. Student submits a question
2. System retrieves relevant chunks from primary source
3. System synthesizes an explanation using document content
4. System validates explanation through 3 pipelines
5. System appends citations
6. Answer is displayed to student

#### Output Format

```
Question: [Student's question]

Answer:
[Synthesized explanation using exact terminology and
 examples from the document. Multiple paragraphs allowed.
 Focus on clarity while maintaining technical accuracy.]

Citations: [Page X], [Page Y], [Page Z]
OR
Reference: [Source Name](URL) for URL-based sources

Pipeline Status:
Entailment: Passed (0.74)
Consistency: Passed (0.81)
Token Confidence: Passed (0.69)
```

#### Example Interaction

**Student Input:**
```
"Explain the Nernst equation and how it applies to the 
examples in Chapter 5."
```

**System Output:**
```
Question: Explain the Nernst equation and how it applies 
           to the examples in Chapter 5.

Answer:
The Nernst equation, as described in Chapter 5, is a 
fundamental relationship in electrochemistry that predicts 
the reduction potential of an electrochemical cell under 
non-standard conditions. The standard form is: 
E = E° + (RT/nF) ln(Q)

Where E is the cell potential, E° is the standard reduction 
potential, R is the gas constant, T is temperature, n is the 
number of electrons, F is Faraday's constant, and Q is the 
reaction quotient.

In the examples presented in Chapter 5, the equation is 
applied to several real-world scenarios. For instance, in 
Example 5.2 on page 156, a galvanic cell with non-standard 
concentrations is analyzed using the Nernst equation to 
predict its actual voltage output. The calculation 
demonstrates that as the concentration ratio changes, the 
cell potential deviates from the standard potential 
according to the logarithmic relationship.

The practical significance, as emphasized in the text, is 
that the Nernst equation allows prediction of cell behavior 
under conditions that do not match standard laboratory 
conditions (25°C, 1M concentrations, 1 atm pressure).

Citations: [Page 142-145], [Page 156]

Pipeline Status:
Entailment: Passed (0.78)
Consistency: Passed (0.85)
Token Confidence: Passed (0.72)
```

#### Independence

This is the **ONLY feature** where the system synthesizes and explains concepts in its own words. All other student features either extract, verify, guide, or test, but do not synthesize explanations.

#### Monetization

Premium feature for individuals. Unlimited for institutional subscribers.

---

### STUDENT FEATURE 2: PROBLEM NAVIGATOR (Guided Problem-Solving)

#### Purpose

The student is stuck on a specific problem, derivation, formula, or coding task from their course material. The system walks the student through the conceptual framework and approach required to solve it WITHOUT providing the answer, calculation, or code solution.

#### Functionality

1. Student submits a problem they are stuck on
2. System retrieves the relevant methodology from source
3. System extracts the step-by-step approach (NOT solution)
4. System validates that guidance is grounded in source
5. System presents scaffolded framework to student
6. Student must execute the solution themselves

#### Output Format

```
Problem: [Student's problem statement]

Guided Approach:

Step 1: [Conceptual description of first step]
        Reference: [Page X] describes this methodology.
        Key insight: [What the student should understand]

Step 2: [Conceptual description of second step]
        Reference: [Page Y] shows how to set this up.
        Question to consider: [Guiding question]

Step 3: [Conceptual description of third step]
        Reference: [Page Z] provides the framework.
        Common mistake to avoid: [Misconception]

Step 4: [Conceptual description of final step]
        Reference: [Page W] describes verification.

Next Action:
Attempt the problem yourself using these steps.
You must perform the actual calculation/coding.
If you get stuck on a specific step, ask again.

Pipeline Status: Passed
```

#### Example Interaction

**Student Input:**
```
"I'm stuck on Problem 7 in Chapter 3. It asks me to solve 
dJ/dw = 0 for the cost function. I don't know where to 
start."
```

**System Output:**
```
Problem: Solve dJ/dw = 0 for the cost function in 
          Problem 7, Chapter 3.

Guided Approach:

Step 1: Identify the cost function type.
        Reference: [Page 89] describes three types of 
        cost functions used in this chapter.
        Your task: Which type appears in Problem 7?

Step 2: Write out the mathematical form.
        Reference: [Page 91] shows the general form for 
        each cost function type.
        Your task: Substitute your specific parameters 
                   into this form.

Step 3: Apply differentiation.
        Reference: [Page 93] demonstrates the 
        differentiation rules used in this chapter.
        Your task: Differentiate your cost function with 
                   respect to w.

Step 4: Set the derivative equal to zero.
        Reference: [Page 95] explains why setting 
        dJ/dw = 0 finds the minimum.
        Your task: Solve the resulting equation for w.

Step 5: Verify your answer.
        Reference: [Page 97] shows how to check if your 
        solution is a minimum (not a maximum).
        Your task: Apply the second derivative test.

Next Action:
Work through these steps now. Show me your work at any step 
where you get stuck, and I will provide more specific 
guidance.

Pipeline Status: Passed
```

#### Independence

This is the **ONLY feature** that teaches methodology and approach without providing solutions. It is distinct from Concept Guide (which explains what something is) in that it teaches how to use a methodology to solve a specific problem.

#### Monetization

Premium feature. Students subscribe for unlimited problem guidance sessions.

---

### STUDENT FEATURE 3: SUBMISSION VALIDATOR (Essay/Assignment Auditor)

#### Purpose

The student submits a draft essay, lab report, or long-form assignment. The system audits the submission sentence-by-sentence against the source material. It flags any deviation, unsupported claim, or external information the student has introduced. The student receives detailed, actionable feedback before official submission.

#### Functionality

1. Student uploads assignment text
2. System chunks the student's text into sentences
3. System checks each sentence against source material
4. System applies entailment pipeline to each claim
5. System identifies flagged sentences
6. System provides corrections with page references
7. System returns detailed audit report

#### Output Format

```
Assignment Audit Complete

Overall Assessment: [Number] sentences passed,
                   [Number] sentences flagged

PASSED SENTENCES:
[Count] sentences are well-grounded in the source.
No action required.

FLAGGED SENTENCES:

Flagged Sentence [N] (Line [X]):
'Quoted sentence from student submission'

Issue Type: [Overgeneralization / Contradiction / 
             External Information / Unsupported Claim / 
             Incomplete Statement]

Explanation: [Why this sentence is problematic]

Source Correction: Reference: [Page X] or
                   Reference: [Source](URL)
                   'Correct information from source'

Suggested Revision: [How the student should rewrite the 
                     sentence based on source]

[Repeat for each flagged sentence]

Action Items:
1. [Revision needed for sentence in line X]
2. [Additional research needed for topic Y]
3. [Clarification needed on concept Z]
```

#### Example Interaction

**Student Input:**
```
[Uploads 500-word essay on Chapter 7]
```

**System Output:**
```
Assignment Audit Complete

Overall Assessment: 38 sentences passed,
                   3 sentences flagged

PASSED SENTENCES:
38 sentences are well-grounded in the source.
These include your discussion of mechanisms, your analysis 
of examples, and your conclusions.
No action required for these sections.

FLAGGED SENTENCES:

Flagged Sentence 1 (Line 12):
'Photosynthesis occurs only in the leaves.'

Issue Type: Overgeneralization

Explanation: Your statement is too absolute. The document 
explicitly states that photosynthesis occurs primarily in 
leaves but also in stems and algae under specific conditions. 
Your phrasing excludes valid biological structures.

Source Correction: [Page 73]
'While photosynthesis is most efficient in leaves, it also 
occurs in stems and algae when exposed to sufficient light 
and under appropriate environmental conditions.'

Suggested Revision: 'Photosynthesis occurs most efficiently 
in leaves, but also in stems and algae under appropriate 
conditions.'

---

Flagged Sentence 2 (Line 28):
'The rate of photosynthesis is constant.'

Issue Type: Contradiction

Explanation: This contradicts your course material. Your 
textbook describes variable photosynthesis rates based on 
multiple environmental factors. By stating the rate is 
constant, you are providing incorrect information.

Source Correction: [Page 75]
'The rate of photosynthesis depends on light intensity, 
temperature, and CO2 concentration. As any of these factors 
increases, the photosynthesis rate increases until a maximum 
rate is reached, beyond which further increases have no 
effect.'

Suggested Revision: 'The rate of photosynthesis varies based 
on light intensity, temperature, and CO2 concentration.'

---

Flagged Sentence 3 (Line 45):
'Scientists discovered this mechanism in 1952.'

Issue Type: External Information

Explanation: Your course material does not mention a 
discovery date for this mechanism. This appears to be 
external information you introduced. Either remove the date 
or provide your external source.

Source Status: Not found in [Chapter 7]

Action Required: Either remove the date from your essay, or 
find and cite your external source. If you want to include 
this historical fact, it must come from a verified source 
you can cite outside your textbook.

---

Action Items:
1. Revise Sentence 1 (Line 12) to avoid overgeneralization
2. Revise Sentence 2 (Line 28) to accurately reflect 
   variable rates
3. Either remove the date in Sentence 3 (Line 45) or 
   source it externally

Resubmit your revised essay for another audit.
```

#### Independence

This is the **ONLY feature** that audits existing student work rather than generating new content. It is distinct from Concept Guide and Problem Navigator in that it does not teach or explain; it verifies accuracy.

#### Monetization

Premium feature. Institutions purchase per-student licenses for assignment platforms.

---

### STUDENT FEATURE 4: EXAM SIMULATOR (Adaptive Real-Time Testing)

#### Purpose

The student initiates exam simulation mode and specifies exam parameters (chapters, time limit, question count). The system generates questions from the document in real-time, adapting difficulty based on student responses. The student receives a final score with topic-by-topic breakdown and exact page references for every incorrect answer showing where to study.

#### Functionality

1. Student initiates exam simulation with parameters
2. System generates first question at baseline difficulty
3. System presents question and student responds
4. System evaluates response through entailment pipeline
5. System adapts next question difficulty based on performance (correct = harder, incorrect = similar)
6. System continues until time expires or question limit
7. System generates comprehensive performance report

#### Output Format

```
Exam Simulation Initiated
Topic: [Chapters specified]
Difficulty: Adaptive
Time Limit: [Minutes]
Question Limit: [Number]

[During Exam - Each Question]

Question [N] (Difficulty: [Low/Medium/High])
[Question text grounded in source material]

[Student provides answer]

[System evaluates answer]

Correct. Points: [X]/[Y]
[Brief explanation of why answer is correct]
Difficulty Next Question: Increased

OR

Incorrect. Points: [0]/[Y]
Correct Answer: [Answer]
Explanation: [Why student's answer was wrong]
Correct Source Reference: [Page X] or Reference: [URL]
Difficulty Next Question: Similar/Reduced

[After all questions complete]

EXAM COMPLETE

FINAL SCORE: [Points]/[Total Points] ([Percentage]%)

TOPIC BREAKDOWN:
[Topic 1]: [Score]/[Max] ([Percentage]%) - [Assessment]
[Topic 2]: [Score]/[Max] ([Percentage]%) - [Assessment]
[Topic 3]: [Score]/[Max] ([Percentage]%) - [Assessment]

Assessment Scale:
90-100%: Mastery
80-89%: Strong
70-79%: Developing
60-69%: Review Needed
Below 60%: Requires Intervention

AREAS REQUIRING STUDY:
Topic: [Topic Name]
Your Score: [X]%
You missed [N] questions on this topic.
Review [Page X-Y] before retaking.

Topic: [Topic Name]
Your Score: [X]%
You missed [N] questions on this topic.
Focus on [specific concept] - see [Page Z].

RECOMMENDED NEXT STEPS:
1. Study flagged chapters using Concept Guide feature
2. Practice problem-solving using Problem Navigator
3. Review assignment feedback using Submission Validator
4. Retake this exam in [recommended timeframe]

Would you like to:
a) Retake this exam (same parameters)
b) Retake with increased difficulty
c) Focus exam on specific topics you struggled with
d) Exit simulation
```

#### Example Interaction

**Student Input:**
```
"Simulate an exam on Chapters 1-5. 60 minutes, 25 questions, 
adaptive difficulty."
```

**System Output:**
```
Exam Simulation Started
Topics: Chapters 1-5
Duration: 60 minutes
Question Limit: 25 questions
Difficulty: Adaptive

Question 1 (Difficulty: Low, Chapter 1): [Page 15]
According to the text, the primary definition of 
photosynthesis is:
a) Conversion of sunlight to chemical energy
b) Conversion of chemical energy to sunlight
c) Breakdown of glucose molecules
d) Production of chlorophyll

[Student selects: a]

Correct. Points: 1/1
Photosynthesis is indeed the conversion of light energy 
into chemical energy stored in glucose.
Difficulty Next Question: Medium

[Questions 2-12 proceed with adaptive difficulty]

Question 13 (Difficulty: Hard, Chapter 4): [Page 89-92]
A student observes that a plant under blue light produces 
more oxygen than under red light. Based on the light 
absorption spectrum described in Chapter 4, which pigment 
is primarily responsible for this observation?

[Student selects: Chlorophyll a]

Incorrect. Points: 0/1
Correct Answer: Chlorophyll b
Explanation: According to the absorption spectrum in 
Chapter 4, chlorophyll b has peak absorption in the blue 
wavelength range (420-450 nm), making it primarily 
responsible for blue light capture. Chlorophyll a has peak 
absorption in red wavelengths.
Review [Page 91] for the complete absorption spectrum.
Difficulty Next Question: Similar

[Questions 14-25 proceed]

EXAM COMPLETE

FINAL SCORE: 18/25 (72%)

TOPIC BREAKDOWN:
Chapter 1 (Basics):         5/5 (100%) - Mastery
Chapter 2 (Mechanisms):     4/5 (80%)  - Strong
Chapter 3 (Processes):      5/5 (100%) - Mastery
Chapter 4 (Advanced):       2/5 (40%)  - Review Needed
Chapter 5 (Integration):    2/5 (40%)  - Review Needed

AREAS REQUIRING STUDY:
Topic: Photosynthetic Pigments (Chapter 4)
Your Score: 40%
You missed 3 questions on pigment absorption.
Focus on the absorption spectrum [Page 91-92].
Study the distinction between chlorophyll a and b.

Topic: Respiration Integration (Chapter 5)
Your Score: 40%
You missed 3 questions on ATP production.
Review the connection between photosynthesis and cellular 
respiration [Page 103-107].

RECOMMENDED NEXT STEPS:
1. Use Concept Guide to review photosynthetic pigments 
   and respiration integration
2. Use Problem Navigator to practice calculations on ATP 
   production from glucose
3. Retake this exam in 2-3 days after review

Would you like to:
a) Retake this exam (same parameters)
b) Retake with focus on Chapter 4 and 5
c) Exit simulation
```

#### Independence

This is the **ONLY feature** that provides adaptive, timed testing with real-time performance tracking. Unlike Concept Guide, it tests knowledge rather than teaching. Unlike Problem Navigator, it evaluates answers rather than guiding approaches.

#### Monetization

Premium subscription for individuals (monthly/yearly). Institutional licensing for schools.

---

## PART 4: TEACHER FEATURES

All teacher features below MUST pass the 3-Pipeline Gatekeeper before any output is shown to the teacher.

---

### TEACHER FEATURE 1: ASSIGNMENT GRADER (Objective, Automated Assessment)

#### Purpose

The teacher uploads student submissions (essays, reports, problem solutions, test answers) alongside a grading rubric or answer key. The system evaluates each submission objectively against the source document, providing detailed feedback on every student's work. The system grades consistently, removes bias, and enables appeal-proof grading decisions.

#### Functionality

1. Teacher uploads student submissions in batch
2. Teacher provides grading rubric or answer key
3. System extracts claims from each submission
4. System checks each claim against source material
5. System applies entailment pipeline to each claim
6. System assigns grades based on rubric
7. System generates detailed feedback per student
8. System produces class summary report

#### Output Format

```
Assignment Grading Complete: [N] submissions in [time] seconds

INDIVIDUAL STUDENT FEEDBACK:

STUDENT [N]: [Student Name/ID]
ASSIGNMENT: [Assignment name]
GRADE: [Letter grade] ([Numerical score]/100)

Strengths:
- [Positive assessment 1 with citation]
- [Positive assessment 2 with citation]
- [Positive assessment 3 with citation]

Areas for Improvement:
- [Gap 1 with source reference]
- [Gap 2 with source reference]
- [Gap 3 with source reference]

Detailed Feedback:
[Section-by-section breakdown of strengths and weaknesses 
 with direct references to source material]

Suggested Resources for Student:
[Page X] to review concept A
[Page Y] to practice concept B

[Repeat for each student]

CLASS SUMMARY:

Average Grade: [X]/100
Grade Distribution:
  A (90-100): [N] students
  B (80-89):  [N] students
  C (70-79):  [N] students
  D (60-69):  [N] students
  F (Below 60): [N] students

TOPICS MOST FREQUENTLY MISSED:

Topic [A]: [Percentage]% of students had issues
Concept: [Specific concept students struggled with]
Source Reference: [Page X]
Recommendation: Reteach this concept before next unit

Topic [B]: [Percentage]% of students had issues
Concept: [Specific concept students struggled with]
Source Reference: [Page Y]
Recommendation: Provide additional practice problems

OVERALL CLASS ASSESSMENT:
[Summary of class performance]
[Recommendations for next steps]
```

#### Example Interaction

**Teacher Input:**
```
"Grade 150 essays on Chapter 7.
Rubric: Accuracy to text (40%), Depth of analysis (30%), 
Writing quality (30%).
Provide detailed feedback for each student."
```

**System Output:**
```
Assignment Grading Complete: 150 submissions in 45 seconds

INDIVIDUAL STUDENT FEEDBACK:

STUDENT 1: Sarah Chen
ASSIGNMENT: Chapter 7 Analysis Essay
GRADE: A (94/100)

Strengths:
- Comprehensive understanding of photosynthetic mechanisms 
  [Page 73]. You correctly identified all five reaction 
  types and their relationships.
- Excellent use of evidence from the text [Page 74-75]. 
  Your examples are directly relevant and properly 
  integrated.
- Clear, well-organized essay structure. Your argument 
  progression is logical and easy to follow.

Areas for Improvement:
- Could have connected concepts to the examples in 
  Chapter 8. Your essay would be stronger with this 
  synthesis across chapters.
- Minor: One technical term used slightly inaccurately. 
  See [Page 71] for the precise definition.

Detailed Feedback:
Your essay demonstrates strong mastery of Chapter 7 content. 
Your explanation of the light-dependent and light-independent 
reactions is accurate and thorough. Your use of the examples 
on [Page 74] is particularly effective in illustrating these 
processes. The only area for growth would be connecting these 
mechanisms to the broader context in Chapter 8, which 
discusses how different organisms optimize these processes.

Suggested Resources:
[Page 74-75] - Review these examples (you used them well)
[Page 103] - Chapter 8 overview for future synthesis

---

STUDENT 2: Marcus Johnson
ASSIGNMENT: Chapter 7 Analysis Essay
GRADE: C+ (78/100)

Strengths:
- You demonstrated understanding of the basic 
  photosynthetic process [Page 72-73].
- Your writing is clear and easy to read.

Areas for Improvement:
- Missing discussion of the Calvin Cycle [Page 78-80]. 
  This is a major concept in Chapter 7 and your essay 
  does not address it.
- Over-simplified explanation of the electron transport 
  chain. [Page 76] provides more detail than you 
  included.
- Missing evidence and citations. While you mention 
  concepts correctly, you did not support your 
  statements with specific examples from the text.

Detailed Feedback:
Your essay covers the basic light-dependent reactions, but 
it lacks the depth and detail expected for this assignment. 
Specifically:

1. The Calvin Cycle is discussed in [Page 78-80] and is 
   central to photosynthesis. Your omission of this 
   section significantly limits your analysis.

2. Your explanation of electron transport [Page 76] is too 
   brief. The text provides important details about how 
   electrons move through the thylakoid membrane that 
   would strengthen your understanding.

3. You make correct statements but without supporting 
   evidence. For example, you say 'photosynthesis happens 
   in two main parts,' which is correct, but you should 
   cite [Page 72] and provide the specific names and 
   locations of these two parts.

Suggested Resources:
[Page 78-80] - Study the Calvin Cycle (not covered in 
              your essay)
[Page 76] - Reread the electron transport details
[Page 74-75] - Use these examples to support your points

---

[... 148 more detailed breakdowns ...]

CLASS SUMMARY:

Average Grade: 74/100
Grade Distribution:
  A (90-100): 12 students
  B (80-89):  45 students
  C (70-79):  78 students
  D (60-69):  10 students
  F (Below 60): 5 students

TOPICS MOST FREQUENTLY MISSED:

Topic 1: Calvin Cycle / Light-Independent Reactions
Frequency: 40% of students had significant issues
Concept: Students struggled to explain how the Calvin Cycle 
         uses ATP and NADPH from light reactions to produce 
         glucose.
Source Reference: [Page 78-80]
Student Error Pattern: Most students omitted or 
                       oversimplified this section.
Recommendation: Reteach the Calvin Cycle with visual 
                diagrams (Page 79). Allocate 2 additional 
                class periods before moving to Chapter 8.

Topic 2: Electron Transport Chain
Frequency: 55% of students had issues
Concept: Students did not understand the detailed mechanism 
         of how electrons move through protein complexes 
         in the thylakoid membrane.
Source Reference: [Page 76-77]
Student Error Pattern: Most students provided a vague 
                       explanation rather than the specific 
                       protein complexes (PSI, PSII, 
                       Cytochrome b6f).
Recommendation: Provide additional practice with [Page 76-77]. 
                Consider creating a physical model activity to 
                demonstrate electron flow.

Topic 3: Stoichiometry of ATP Production
Frequency: 25% of students had issues
Concept: Students struggled to calculate the number of ATP 
         molecules produced per glucose molecule.
Source Reference: [Page 81-82]
Student Error Pattern: Calculation errors and conceptual 
                       confusion about proton gradients.
Recommendation: Review [Page 81-82] calculations with worked 
                examples before final exam.

OVERALL CLASS ASSESSMENT:
The class demonstrates a solid foundational understanding of 
photosynthesis. Performance was strong on the light-dependent 
reactions (average 82%) but weak on the light-independent 
reactions (average 65%).

The class average of 74% suggests students need additional 
review before proceeding to Chapter 8.

Specific Recommendations:
1. Reteach the Calvin Cycle with emphasis on [Page 78-80]
2. Provide worked examples of ATP calculations
3. Use visual aids and models for electron transport
4. Schedule a review session before the Chapter 8 test
5. Consider pairing lower-performing students with peer 
   tutors who scored A/B grades
```

#### Independence

This is the **ONLY feature** that grades student work at scale. It uses source documents as ground truth for objective assessment.

#### Monetization

Institutional licensing. Schools purchase per-teacher or per-student licenses. Significant time savings justifies premium pricing.

---

### TEACHER FEATURE 2: EXAM GENERATOR (Automated Assessment Creation)

#### Purpose

The teacher specifies exam parameters (chapters to cover, number of questions, difficulty distribution, question types, time limit). The system generates a complete, well-structured exam grounded 100% in the uploaded course material. The teacher receives a fully formatted exam ready for distribution and an answer key with detailed rationales for every question.

#### Functionality

1. Teacher specifies exam parameters
2. System identifies relevant content from source
3. System generates questions grounded in source
4. System validates each question through pipelines
5. System applies question type (MC, short answer, etc.)
6. System formats exam for distribution
7. System creates detailed answer key with rationales

#### Output Format

```
Exam Generated Successfully

EXAM METADATA:
Title: [Exam title]
Topics: [Chapters/sections covered]
Duration: [Time limit]
Total Points: [Points]
Question Count: [Number]
Difficulty Distribution: [Easy X%, Medium X%, Hard X%]

EXAM DOCUMENT:

[School/Class name]
[Exam Title]
[Instructions to students]

SECTION 1: MULTIPLE CHOICE QUESTIONS

Q1. [Question text grounded in source]
A) [Option grounded in source]
B) [Option grounded in source]
C) [Option grounded in source]
D) [Option grounded in source]

Points: [X]/[Y]

[Q2 through QN...]

SECTION 2: SHORT ANSWER QUESTIONS

Q[N+1]. [Question grounded in source]
(Expected answer length: X words)

Points: [X]/[Y]

[Q[N+2] through Q[Final]...]

ANSWER KEY & DETAILED RATIONALES:

Q1. Correct Answer: [Letter]

Why This Answer is Correct:
[Explanation grounded in source with specific reference]
Source: [Page X] states: '[Relevant quote]'

Why Other Options are Incorrect:
A) [Explanation of why A is wrong - often addressing 
   common misconception or related but different concept]
B) [Explanation of why B is wrong]
C) [Explanation of why C is wrong]

Difficulty Level: [Low/Medium/High]
Topic Tested: [Specific concept/learning objective]
Source Reference: [Page X]

[Q2 through QN...]

SHORT ANSWER ANSWER KEY:

Q[N+1]. Model Answer:
[Expected response paraphrased from source material]

Grading Rubric:
[X] points: Captures all key elements (terms A, B, C)
[X] points: Captures most key elements
[X] points: Captures core concept but missing detail
[X] points: Partial understanding or incomplete response
[X] points: Minimal understanding or significant errors
[0] points: Incorrect or blank

Source Material: [Page X-Y] contains the relevant 
                information for this answer.

[Q[N+2] through Q[Final]...]

EXAM QUALITY REPORT:

Coverage Analysis:
[Topic 1]: [X] questions
[Topic 2]: [X] questions
[Topic 3]: [X] questions

Difficulty Balance:
Easy (0-30% discrimination): [X]%
Medium (30-70% discrimination): [X]%
Hard (70-100% discrimination): [X]%

Learning Objectives Covered:
[Objective 1]: [Questions testing this]
[Objective 2]: [Questions testing this]
[Objective 3]: [Questions testing this]

Scope Validation:
All questions are grounded in the source material.
No out-of-scope content included.
No external knowledge required beyond provided text.
```

#### Example Interaction

**Teacher Input:**
```
"Generate a midterm exam.
Topics: Chapters 1-5
Format: 30 multiple choice, 5 short answer
Difficulty: 25% easy, 50% medium, 25% hard
Time limit: 90 minutes
Provide a detailed answer key with rationales."
```

**System Output:**
```
Exam Generated Successfully

EXAM METADATA:
Title: Biology 101 - Photosynthesis Unit Midterm
Topics: Chapters 1-5 (Introduction to Photosynthesis)
Duration: 90 minutes
Total Points: 50 points
Question Count: 35 (30 MC + 5 SA)
Difficulty Distribution: 25% easy, 50% medium, 25% hard

EXAM DOCUMENT:

BIOLOGY 101 - MIDTERM EXAMINATION
Photosynthesis Unit (Chapters 1-5)
Date: [Date]
Time Limit: 90 minutes
Total Points: 50 points

INSTRUCTIONS TO STUDENTS:
This exam tests your understanding of photosynthesis concepts 
covered in Chapters 1-5. Use only your textbook and class 
notes if allowed. Answer all questions. Show your work for 
calculations.

SECTION 1: MULTIPLE CHOICE QUESTIONS (30 points)
Select the BEST answer for each question.
1 point per question.

Q1 (Easy, Chapter 1): [Page 12]
According to Chapter 1, the primary definition of 
photosynthesis is:
A) The synthesis of glucose from light energy
B) The breakdown of glucose to release energy
C) The conversion of light energy into chemical energy 
   stored in glucose
D) The production of oxygen as a byproduct

Points: 1

Q2 (Medium, Chapters 1-2): [Page 35-38]
Which of the following statements best describes the 
relationship between the light-dependent and 
light-independent reactions?
A) They occur in different organelles
B) They occur at different times of day
C) The products of light-dependent reactions are used by 
   light-independent reactions
D) They are completely independent processes

Points: 1

[Q3 through Q30...]

SECTION 2: SHORT ANSWER QUESTIONS (20 points)
Answer each question in 2-3 sentences using your own words. 
4 points per question.

Q31 (Medium, Chapter 2): [Page 73-75]
Explain how the structure of the chloroplast supports its 
function in photosynthesis.

Answer Length: 2-3 sentences
Points: 4

Q32 (Hard, Chapters 3-4): [Page 89-92]
A scientist observes that a plant produces less oxygen 
under blue light compared to red light. Based on the pigment 
absorption spectra in Chapter 4, explain why this occurs.

Answer Length: 2-3 sentences
Points: 4

[Q33 through Q35...]

---ANSWER KEY & DETAILED RATIONALES---

Q1. Correct Answer: C

Why This Answer is Correct:
[Page 12] explicitly defines photosynthesis as 'a process 
that converts light energy into chemical energy stored in the 
bonds of glucose molecules.' This is the foundational 
definition for the entire unit.

Why Other Options are Incorrect:
A) Incomplete. While glucose synthesis occurs, this does not 
   capture the energy conversion aspect.
B) This is cellular respiration, not photosynthesis.
D) While oxygen is produced, it is a byproduct, not the 
   primary purpose of photosynthesis.

Difficulty Level: Easy
Topic Tested: Definition and fundamental concept
Source Reference: [Page 12]

Q2. Correct Answer: C

Why This Answer is Correct:
[Page 35] states that 'the ATP and NADPH produced in the 
light-dependent reactions serve as energy sources for the 
light-independent reactions.' This describes the functional 
relationship between the two sets of reactions.

Why Other Options are Incorrect:
A) While they occur in different parts of the thylakoid, 
   this does not describe their functional relationship.
B) They both occur during daylight hours when light is 
   available.
D) They are clearly interdependent through ATP and NADPH 
   transfer.

Difficulty Level: Medium
Topic Tested: Integration of concepts across chapters
Source Reference: [Page 35]

[... Q3 through Q30 ...]

Q31. Model Answer:
The chloroplast has a double membrane for protection and 
compartmentalization. The thylakoid membrane system provides 
an extensive surface area for light capture. The stroma 
contains enzymes for the Calvin Cycle reactions.

Grading Rubric:
4 pts: Student mentions all three structural features 
       (double membrane, thylakoid surface area, stroma 
       enzymes) and explains how each supports function.
3 pts: Student mentions two structural features with 
       adequate explanation of function.
2 pts: Student mentions one structural feature with partial 
       explanation of function.
1 pt: Student attempts to connect structure to function but 
      explanation is vague or incomplete.
0 pts: No answer or completely incorrect.

Source Material: [Page 73-75] contains detailed descriptions 
                of chloroplast anatomy and how structure 
                enables photosynthetic function.

[... Q32 through Q35 ...]

EXAM QUALITY REPORT:

Coverage Analysis:
Chapter 1 (Definitions): 5 questions
Chapter 2 (Light Reactions): 10 questions
Chapter 3 (Calvin Cycle): 8 questions
Chapter 4 (Pigments): 7 questions
Chapter 5 (Integration): 5 questions

Difficulty Balance:
Easy (0-30%): 8 questions (23%)
Medium (30-70%): 18 questions (51%)
Hard (70-100%): 9 questions (26%)

Learning Objectives Covered:
Define photosynthesis: Q1, Q6, Q15
Describe light reactions: Q2, Q7, Q9, Q19, Q23, Q31
Explain Calvin Cycle: Q3, Q8, Q12, Q18, Q32
Identify pigments: Q4, Q10, Q16, Q24, Q33
Integrate concepts: Q5, Q11, Q20, Q25, Q34, Q35

Scope Validation:
All 35 questions are grounded in Chapters 1-5.
No external knowledge required.
No out-of-scope content included.
Assessment is ready for distribution.
```

#### Independence

This is the **ONLY feature** that generates complete assessments for teacher use. It creates content rather than grading existing content.

#### Monetization

Institutional licensing. High adoption potential due to time savings (4-8 hours per exam).

---

### TEACHER FEATURE 3: ADAPTIVE FEEDBACK ENGINE (Proactive Tutoring)

#### Purpose

When a student fails a question in Exam Simulator or gets flagged by Submission Validator, the system automatically generates a targeted micro-lesson explaining the exact concept the student missed. The student does not have to ask for help; the system proactively provides scaffolded remediation grounded in their course material.

#### Functionality

1. System detects student knowledge gap (failed question or flagged claim)
2. System identifies the specific concept gap
3. System retrieves relevant material from source
4. System generates targeted explanation (not full lesson)
5. System creates guided practice problem
6. System validates student's attempt
7. System confirms mastery or suggests further study

#### Output Format

```
Knowledge Gap Detected

Failed Question: [Question text that student missed]
Student's Answer: [What the student answered]
Correct Answer: [Correct answer with brief explanation]

MICRO-LESSON: [Concept Name]

You seem to be struggling with: [Concept description]

Let me explain this concept from your course material:

[Targeted explanation from source - keep to 2-3 paragraphs 
 focused on the specific gap, not a full lesson on the topic]

Key Points:
- [Point 1 with reference]
- [Point 2 with reference]
- [Point 3 with reference]

Why Your Answer Was Wrong:
You answered: [Student's response]
This is incorrect because: [Specific explanation of error]

The correct understanding is: [Accurate explanation]

GUIDED PRACTICE:
Now let's practice this concept with a similar problem.
Here is a practice question grounded in your material:

[Practice question, similar structure to failed question]

Try to answer this now using what you just learned.
[Student attempts practice question]

[If correct]
Excellent. You've got it. The key insight is [summary].
You are now ready to tackle similar questions.

[If incorrect]
You're close, but let me clarify one more time...
[Additional explanation focused on the remaining gap]

NEXT STEPS:
1. Review [Page X] in your textbook
2. Complete 3 more practice problems on this concept
3. Use Exam Simulator to test your understanding
4. If you still struggle, use Concept Guide for deeper 
   explanation
```

#### Example Interaction

**Student Interaction:**
```
Student fails Exam Simulator Question 18:
Q18: "According to Chapter 4, which pigment has peak 
      absorption in the blue wavelength?"
Student answers: "Chlorophyll a"
Correct answer: "Chlorophyll b"
```

**System Response:**
```
Knowledge Gap Detected

Failed Question: Which pigment has peak absorption in the 
                blue wavelength?
Student's Answer: Chlorophyll a
Correct Answer: Chlorophyll b

MICRO-LESSON: Photosynthetic Pigment Absorption

You seem to be struggling with the differences between 
chlorophyll a and b absorption spectra. This is a common 
point of confusion, so let me clarify.

[From Page 91 of your textbook]:
'Chlorophyll a has two absorption peaks: one in the blue 
region (430 nm) and one in the red region (662 nm). 
Chlorophyll b has two peaks: one in the blue region 
(453 nm) and one in the red region (645 nm). The key 
difference is that chlorophyll b has a stronger absorption 
peak in the blue region than chlorophyll a.'

In simpler terms:
- Chlorophyll a absorbs most strongly in RED light
- Chlorophyll b absorbs most strongly in BLUE light

Key Points:
- Both pigments absorb blue and red light [Page 91]
- Chlorophyll b's blue peak is stronger [Page 91]
- Chlorophyll a's red peak is stronger [Page 91]
- This is why the answer is chlorophyll b for blue 
  wavelengths [Page 92]

Why Your Answer Was Wrong:
You answered chlorophyll a, but chlorophyll a has its 
STRONGER absorption in the red region, not blue. While 
chlorophyll a does absorb some blue light, chlorophyll b 
has the peak blue absorption.

The correct understanding is:
When asked about blue wavelength absorption, the answer is 
chlorophyll b because it has the maximum absorption peak in 
that region.

GUIDED PRACTICE:
Here's a similar scenario:
A scientist measures the photosynthesis rate under different 
wavelengths using a plant with ONLY chlorophyll a 
(chlorophyll b has been removed). At which wavelength would 
this plant show the HIGHEST photosynthesis rate?

A) 453 nm (blue)
B) 430 nm (blue)
C) 645 nm (red)
D) 662 nm (red)

Try answering this now.
[Student selects: D]

Correct. Excellent. Since only chlorophyll a is present, 
the plant would absorb most strongly at chlorophyll a's peak 
wavelengths, particularly 662 nm in the red region.

NEXT STEPS:
1. Review [Page 91] to cement the pigment differences
2. Complete the practice questions at [Page 95]
3. Retake Exam Simulator Question 18 and similar questions 
   to confirm mastery
4. If you still have questions, use Concept Guide to get a 
   full explanation of photosynthetic pigments
```

#### Independence

This is the **ONLY feature** that provides proactive, targeted remediation to individual students without them requesting help. Unlike Concept Guide (general explanation) or Problem Navigator (guided solving), this feature is reactive to specific failures and provides minimal-sufficient explanation.

#### Monetization

Premium feature for institutions. Included with institutional Exam Simulator and Submission Validator licenses.

---

### TEACHER FEATURE 4: STUDENT RESPONSE ANALYZER (Aggregate Performance Insight)

#### Purpose

After students use Exam Simulator or other assessment tools, the teacher views a comprehensive report showing which specific topics caused the most student confusion and which students need intervention. The report is tied to exact page numbers and concepts so the teacher knows what to reteach and which students to prioritize.

#### Functionality

1. System aggregates data from student assessments
2. System identifies topics with highest failure rates
3. System identifies common misconceptions
4. System flags students requiring intervention
5. System provides reteaching recommendations
6. System links recommendations to source material

#### Output Format

```
STUDENT RESPONSE ANALYSIS REPORT

Analysis Period: [Date range]
Students Assessed: [Number]
Assessments Analyzed: [Types and quantities]

TOPICS WITH HIGHEST FAILURE RATES:

Topic [1]: [Topic Name]
Subject Area: [Chapter X]
Student Failure Rate: [X]%
Assessment Score Average: [X]/100
Status: Review Needed / Strong / Mastery

Detailed Analysis:
[Percentage]% of students struggled with this concept.

Most Common Misconception:
Students frequently answered: '[Wrong answer]'
Correct understanding: '[Correct explanation]'

Source Reference: [Page X] contains the authoritative 
                 explanation of this concept.

Questions Most Often Missed:
- [Question that exposed this gap]
- [Another question that exposed this gap]

Recommended Interventions:
1. Reteach this topic using [Page X-Y] materials
2. Provide additional worked examples from [Page X]
3. Create visual aid/diagram of [concept]
4. Assign supplementary problems from [Page X]
5. Schedule a review session before next assessment

[Repeat for Topic 2, Topic 3, etc...]

STUDENTS REQUIRING INTERVENTION:

Priority Level 1 (Critical - Below 60%):

Student [Name/ID]: [Score]%
Struggling With: [Topics A, B, C with page references]
Recommended Action:
- 1-on-1 tutoring sessions
- Focus on [Topic with lowest score] first [Page X]
- Consider assigning peer tutor who scored [High %]
- Schedule check-in after [timeframe]

Student [Name/ID]: [Score]%
Struggling With: [Topics X, Y, Z with page references]
[Recommendations...]

[Repeat for each critical student]

Priority Level 2 (At Risk - 60-70%):

Student [Name/ID]: [Score]%
Struggling With: [Topics]
Recommended Action: Additional practice and review

[Repeat for each at-risk student]

STUDENTS SHOWING MASTERY (90-100%):

Student [Name/ID]: [Score]%
Strengths: [Topics where student excels]
Recommendation: Consider for peer tutoring or honors 
               extension material [Page X+]

[Repeat for high-performing students]

ACTIONABLE INSIGHTS FOR TEACHING:

Data-Driven Recommendations:
1. Spend additional class time on [Topic with highest 
   failure rate] - specifically [Page X]
2. Use different instructional approach for [Topic] - 
   consider [visual/kinesthetic/collaborative method]
3. Provide practice problems on [Topic] from [Page X]
4. Create study guide covering [Topics] for struggling 
   students
5. Schedule review session before final exam covering 
   [Topic areas with failure rate > 30%]

Pacing Suggestions:
- Current pace: [X days per chapter]
- Recommended pace: [Adjust based on data]
- Chapters needing extension: [List with reasons]
- Chapters students have mastered: [List]

Assessment Insights:
- [Percentage]% of class ready to move forward
- [Percentage]% need additional practice
- [Percentage]% need intervention

Next Steps:
1. Address Priority Level 1 students immediately
2. Implement recommended reteaching on [Topic]
3. Reassess class after intervention [recommend date]
4. Adjust future lesson plans based on this data
```

#### Example Interaction

**Teacher Views Report:**
```
After 150 students take Exam Simulator on Chapters 1-5
```

**System Response:**
```
STUDENT RESPONSE ANALYSIS REPORT

Analysis Period: November 1-15
Students Assessed: 150
Assessments Analyzed: Exam Simulator (150 completions)

TOPICS WITH HIGHEST FAILURE RATES:

Topic 1: Calvin Cycle / Light-Independent Reactions
Subject Area: Chapter 4
Student Failure Rate: 58%
Assessment Score Average: 42/100
Status: Review Needed

Detailed Analysis:
58% of students performed poorly on questions testing the 
Calvin Cycle. This is the single biggest knowledge gap in 
your class right now.

Most Common Misconception:
Students frequently answered: 'The Calvin Cycle produces 
glucose directly from CO2 in a single step.'

Correct understanding: 'The Calvin Cycle is a multi-step 
process that converts CO2 into 3-PG, which is then used to 
regenerate RuBP and produce G3P. Only after multiple turns 
of the cycle is glucose synthesized.'

Source Reference: [Page 78-80] contains a detailed 
               step-by-step explanation of the Calvin 
               Cycle process.

Questions Most Often Missed:
- Q18: 'How many turns of the Calvin Cycle are required to 
        produce one glucose molecule?'
      (70% incorrect)
- Q21: 'In the Calvin Cycle, which molecule is regenerated 
        to continue the cycle?'
      (65% incorrect)
- Q24: 'What is the role of ATP in the Calvin Cycle?'
      (54% incorrect)

Recommended Interventions:
1. Reteach the Calvin Cycle using the detailed breakdown on 
   [Page 78-80]
2. Create a visual step-by-step diagram (perhaps adapted 
   from [Page 79])
3. Use the worked examples on [Page 81] to show how ATP 
   and NADPH are consumed
4. Have students trace one complete turn of the cycle 
   manually with labeled diagrams
5. Schedule a 45-minute review session before the 
   Chapter 5 test
6. Provide the practice problems on [Page 83-84]

---

Topic 2: Stoichiometry and ATP Production
Subject Area: Chapter 4-5
Student Failure Rate: 42%
Assessment Score Average: 58/100
Status: Review Needed

Detailed Analysis:
42% of students struggled with the quantitative aspects of 
photosynthesis, specifically calculating ATP molecules 
produced.

Most Common Misconception:
Students frequently answered: 'Each electron produces one 
ATP molecule as it moves through the electron transport 
chain.'

Correct understanding: 'The relationship between electron 
movement and ATP production is more complex. ATP is produced 
via chemiosmosis as protons are pumped across the thylakoid 
membrane. The stoichiometry is approximately 3 protons per 
ATP produced.'

Source Reference: [Page 76-77] contains the detailed 
               explanation of electron transport chain 
               mechanics and chemiosmosis.

Questions Most Often Missed:
- Q15: 'How many ATP molecules are produced per NADPH 
        formed in the light reactions?'
      (60% incorrect)
- Q22: 'If 10 electrons are passed through the electron 
        transport chain, approximately how many ATP 
        molecules are produced?'
      (65% incorrect)

Recommended Interventions:
1. Review the chemiosmotic hypothesis [Page 76]
2. Work through the stoichiometric calculations with 
   concrete examples [Page 77]
3. Provide students with the equation for calculating ATP 
   yield: [Provide specific formula from text]
4. Assign practice calculations from [Page 82-85]
5. Consider using a simulation or animation to show 
   chemiosmosis in action

---

Topic 3: Pigment Absorption and Light Wavelengths
Subject Area: Chapter 3
Student Failure Rate: 25%
Assessment Score Average: 75/100
Status: Developing

Detailed Analysis:
While 25% still represents a knowledge gap, this topic had 
the lowest failure rate overall. Students demonstrated 
generally solid understanding of wavelength concepts.

Most Common Misconception:
Some students confused which chlorophyll has peak 
absorption in the blue region.

Source Reference: [Page 65] absorption spectrum diagram

Recommended Intervention:
Brief clarification rather than reteaching. Refer students 
to [Page 65] absorption spectrum.

---

STUDENTS REQUIRING INTERVENTION:

Priority Level 1 (Critical - Below 60%):

Student ID 42 (Sarah M.): 42%
Struggling With: Calvin Cycle [Page 78-80],
                Stoichiometry [Page 76-77],
                ATP production [Page 77]
Overall pattern: Conceptual gaps in light-independent 
                 reactions

Recommended Action:
- Assign 1-on-1 tutoring sessions (2x per week)
- Focus first on understanding the Calvin Cycle [Page 78] 
  before moving to stoichiometry
- Consider pairing with Student ID 8 (James T.), who scored 
  96% and understands these concepts well
- Provide simplified study guide covering [Page 78-80]
- Retest after 2 weeks

Student ID 67 (Marcus J.): 55%
Struggling With: Calvin Cycle [Page 78-80],
                Wavelength-pigment relationships [Page 65]

Recommended Action:
- Provide after-school review sessions covering these 
  topics
- Focus on the visual diagrams in [Page 79]
- Assign supplementary practice from [Page 83-84]
- Retest after 1 week

Student ID 89 (Lisa P.): 58%
Struggling With: Stoichiometry [Page 76-77],
                Chemiosmosis mechanics [Page 76]

Recommended Action:
- This student seems strong on conceptual material but weak 
  on quantitative calculations
- Provide targeted math review for stoichiometry
- Work through calculation examples from [Page 77]
- Schedule 30-minute tutoring on just calculation 
  methodology

[List 4 more Priority Level 1 students...]

Priority Level 2 (At Risk - 60-70%):

Student ID 12 (Robert C.): 65%
Struggling With: Calvin Cycle, ATP production
Recommended Action: Additional practice problems

[List 8 more Priority Level 2 students...]

STUDENTS SHOWING MASTERY (90-100%):

Student ID 8 (James T.): 96%
Strengths: All topics. Particularly strong on stoichiometry 
          and Calvin Cycle mechanisms.
Recommendation: Assign as peer tutor for Priority Level 1 
               students. Consider providing honors 
               extension material on [Page 120+] covering 
               advanced topics.

Student ID 25 (Priya K.): 94%
Student ID 33 (David L.): 92%
[List 5 more high-performing students...]

ACTIONABLE INSIGHTS FOR TEACHING:

Data-Driven Recommendations:
1. The Calvin Cycle is your most critical reteach area. 
   Allocate 2 full class periods to [Page 78-80]. Use 
   different teaching approaches (diagram tracing, worked 
   examples, peer teaching).

2. Address stoichiometry and quantitative understanding. 
   10 more students (7%) need math support for ATP 
   calculations. Provide worked examples and practice.

3. Wavelength-pigment relationships need a brief 
   clarification (1 class period) but don't require full 
   reteaching.

Pacing Suggestions:
- Current pace: 1.5 days per chapter
- Recommended pace: 2-2.5 days per chapter for Chapters 4-5
- You are moving too quickly for 40% of your class
- Consider extending Chapter 4 by 1 additional day
- Chapters 1-3 can maintain current pace

Assessment Insights:
- 45% of class (68 students) are ready to move to 
  Chapter 6 content
- 35% of class (52 students) need additional practice 
  before proceeding
- 20% of class (30 students) need intervention on 
  foundational concepts

Next Steps:
1. This week: Identify and meet with Priority Level 1 
   students (10 students). Explain their gaps and provide 
   support plan.
2. Next 2 weeks: Reteach Calvin Cycle and stoichiometry 
   using recommended materials and multiple instructional 
   approaches.
3. Week 3: Conduct reassessment using Exam Simulator.
4. Analyze results and adjust pacing for Chapter 6.
```

#### Independence

This is the **ONLY feature** that aggregates and analyzes class-wide performance data to guide teaching decisions. Unlike Assignment Grader (individual assessment), this feature provides system-wide insights to inform instruction.

#### Monetization

Premium institutional feature. Teachers and departments pay for evidence-based lesson planning and data-driven instruction support.

---

## PART 5: THE CORE ENGINE ARCHITECTURE

### COMPONENT 1: Multi-Agent MCP Orchestrator

**Model:** Gemini 2.5 Flash

**Fallback Cascade** (applies when primary source insufficient):
1. `search_document` -> User-provided local documents
2. `search_arxiv` -> Peer-reviewed research papers
3. `search_copilot` -> AI knowledge base
4. `search_web` -> DuckDuckGo live web

**Orchestrator Rules:**
- Retrieves raw context snippets ONLY
- NOT permitted to formulate final answers
- Tracks source type (local vs online) through entire pipeline
- Passes source metadata to all downstream components
- Stops at first successful retrieval that passes pipelines

---

### COMPONENT 2: 3-Pipeline Gatekeeper (Absolute Core)

**Applies to:** EVERY feature, EVERY output, EVERY user role

#### Execution Order (Optimized for Async/Parallel on M4 Air)

**Step 1:** Run Pipeline 1 and Pipeline 3 in PARALLEL using `asyncio.gather()` as they are independent. This saves 20-30 seconds.

**Step 2:** Fast-Fail Check - If Pipeline 1 OR Pipeline 3 fails → STOP. Reject answer immediately. Do not run Pipeline 2. Try next tool in fallback cascade.

**Step 3:** Run Pipeline 2 ONLY if Step 1 passes. Pipeline 2 is expensive (generates k=2 variants). Only run when absolutely necessary.

#### Pipeline 1 - ENTAILMENT (MiniCheck roberta-large)

- **Function:** Verify every claim is backed by context
- **Threshold:** score >= 0.6
- **Input:** Context (max 500 chars), Answer (max 200 chars)
- **Truncation:** System must truncate inputs aggressively
- **On Fail:** Answer rejected, next tool tried

#### Pipeline 2 - CONSISTENCY (SelfCheckGPT k=2)

- **Function:** Generate 2 answer variants in parallel. Cross-check for contradictions.
- **Method:** Sentence-transformers embedding similarity
- **Model:** all-MiniLM-L6-v2 on device MPS
- **Threshold:** score >= 0.5
- **Runs Only After:** Pipeline 1 AND 3 pass
- **On Fail:** Answer rejected, next tool tried

#### Pipeline 3 - TOKEN CONFIDENCE (Logistic Regression)

- **Function:** Calculate token probability distribution
- **Method:** Logprobs of generated tokens + sequence length
- **Threshold:** score >= 0.5
- **On Fail:** Answer rejected, next tool tried

#### Strict Mode Refusal

- **Trigger:** ALL tools exhausted AND ALL pipelines failed
- **Action:** Synthesizer agent generates formal refusal
- **Content:** Explains precisely which pipelines failed and why the answer cannot be provided
- **Citation:** None
- **UI:** Grey banner

---

### COMPONENT 3: Intelligent Query Rewriting

**Model:** Gemini 2.5 Flash

**Behavior:**
- Monitors conversation history
- Detects vague or incomplete follow-ups
- Rewrites into self-contained, precise queries
- Runs in PARALLEL with document search using `asyncio.create_task()` (does not block)

**Skip Rewriting If:**
- No conversation history exists
- Question contains more than 8 words
- Question is already self-contained

---

### COMPONENT 4: Two-Layer Semantic Cache (CAG)

#### Layer 1 - RAM Cache

- **Storage:** Last 100 verified question embeddings
- **Priority:** Checked FIRST before any database query
- **Threshold:** 0.92 cosine similarity
- **Speed:** Response in under 10 milliseconds
- **Model:** all-MiniLM-L6-v2 on MPS

#### Layer 2 - PostgreSQL Cache

- **Priority:** Checked only on RAM cache miss
- **On Hit:** Result promoted to RAM cache immediately
- **On Store:** Saved to both layers simultaneously
- **Rule:** ONLY pipeline-verified answers are cached
- **Metadata:** Source type (local vs online) stored alongside every cached answer to preserve citation logic on cache hit

---

### COMPONENT 5: Hybrid Document Search

- LangChain text splitters for chunking
- PostgreSQL + pgvector for embeddings
- Cosine similarity search for retrieval
- Returns top 3 most relevant chunks
- Source type metadata attached to every chunk and passed through entire pipeline to citation layer

---

## PART 6: HARDWARE CONSTRAINTS AND CONFIGURATION

### Hardware Specifications

- **Device:** MacBook Air M4
- **RAM:** 16GB (shared CPU/GPU)
- **Storage:** 512GB
- **Compute Target:** MPS (Metal Performance Shaders)

### RAM Budget Allocation

```
macOS System:          ~3.0 GB
Qwen2.5 7B (q4_K_M):  ~4.5 GB
MiniCheck roberta:     ~1.5 GB
PostgreSQL + pgvector: ~0.5 GB
React Frontend:        ~0.5 GB
Python Backend:        ~1.0 GB
Available Buffer:      ~4.5 GB
```

### Ollama Optimized Settings (Qwen2.5 7B q4_K_M)

```
num_ctx        = 2048
num_gpu        = 99
num_thread     = 8
num_batch      = 512
num_predict    = 300
temperature    = 0.3
top_k          = 20
top_p          = 0.9
repeat_penalty = 1.1
```

---

## PART 7: FRONTEND UI SPECIFICATIONS

### Framework & Tone

- **Framework:** React
- **Tone:** Completely formal academic tone. No emojis anywhere.
- **Math Rendering:** LaTeX ($$...$$)
- **Text Rendering:** Native Markdown

### Citation Rendering by Source Type

- **Local document:** `[Page X]` or `[Section: Name]` inline
- **URL-based:** `Reference: [Source Name](URL)` at bottom
- **Refusal:** No citation shown

### Source Banners (Formal Text Labels)

- **Local (default):** No banner
- **ArXiv:** `Source: Academic Research (ArXiv)`
- **Copilot:** `Source: AI Knowledge Base (Copilot)`
- **Web:** `Source: Live Web Search`
- **Refusal:** `FactShield Strict Mode Refusal`

### Pipeline Status Display (Shown on All Outputs)

```
Entailment     : Passed (0.74)
Consistency    : Passed (0.81)
Token Confidence: Passed (0.69)
```

Or on failure:
```
Entailment     : Failed (0.42) - Answer Rejected
```

---

## PART 8: ABSOLUTE RULES (NEVER VIOLATE)

### VALIDATION RULES

1. Pipeline 1 threshold must remain at 0.6 or above
2. Pipeline 2 threshold must remain at 0.5 or above
3. Pipeline 3 threshold must remain at 0.5 or above
4. All 3 pipelines must pass for any output to be shown
5. Pipeline 2 runs only after Pipeline 1 and 3 pass
6. Every feature for every user passes all 3 pipelines

### ORCHESTRATION RULES

7. Fallback cascade order: Document -> ArXiv -> Copilot -> Web. Never change this order.
8. Orchestrator must NOT formulate final answers
9. Strict Mode Refusal triggers when all tools fail

### CITATION RULES

10. Local source -> `[Page X]` or `[Section]` only. No URL.
11. Online source -> Full URL citation is mandatory.
12. If source type cannot be determined -> Reject answer.
13. Source type metadata must be preserved through cache so citation logic remains correct on cache hit.

### TONE AND PRESENTATION RULES

14. No emojis anywhere in the system at any point
15. Formal academic tone throughout all output
16. Source banners use formal text labels only
17. Pipeline status displayed formally on all outputs

### SYSTEM INTEGRITY RULES

18. FactShield must never hallucinate or guess
19. LaTeX formatting must be preserved in all outputs
20. Cache stores only pipeline-verified answers

---

## PART 9: YOUR INSTRUCTIONS (CRITICAL - READ CAREFULLY)

You are now the lead AI developer for FactShield. You will:

### 1. ACKNOWLEDGE UNDERSTANDING

Confirm in detail that you understand:
- The 8 independent features (4 student, 4 teacher)
- The universal citation rules (local vs online)
- The 3-Pipeline Gatekeeper system
- The M4 hardware constraints
- The formal, no-emoji tone requirement
- The Orchestrator fallback cascade
- The two-layer caching architecture

### 2. REQUEST REQUIRED INFORMATION

Ask for:
- Your current backend project structure
- Your core routing/API file (e.g., main.py, app.py)
- Your vector database schema
- Your PostgreSQL connection details
- Your current model integration code
- Any existing pipeline validation code

**Do NOT write code until you have these files.**

### 3. IMPLEMENTATION PROTOCOL

When you begin writing code:

a) Use these comment tags on EVERY important section:
```python
# OPTIMIZED: [reason for optimization]
# RULE: [which absolute rule this enforces]
# PIPELINE: [which pipeline validation]
# CITATION: [how citation logic is handled]
# SOURCE: [how source type is tracked]
```

b) After each complete feature implementation:
- Provide exact terminal commands to test it
- Explain what to expect as output
- Describe any required configuration changes
- List any new dependencies to install

c) Do NOT write code for multiple features at once. Implement one feature completely, test it, then move to the next feature.

d) Always prioritize speed optimization for M4 Air:
- Use async/parallel execution where possible
- Use truncation to reduce computation
- Use fast-fail strategies in pipelines
- Minimize RAM usage

### 4. FEATURE IMPLEMENTATION ORDER

**Recommended sequence:**

**Phase 1 (Week 1):**
- Concept Guide (student)
- Assignment Grader (teacher)

**Phase 2 (Week 2):**
- Problem Navigator (student)
- Exam Generator (teacher)

**Phase 3 (Week 3):**
- Submission Validator (student)
- Adaptive Feedback (teacher)

**Phase 4 (Week 4):**
- Exam Simulator (student)
- Response Analyzer (teacher)

### 5. TESTING PROTOCOL

After each feature:
- Write a test case that exercises the full pipeline
- Verify all 3 pipelines execute correctly
- Confirm citations render correctly (local vs online)
- Test async execution on M4 (use Activity Monitor)
- Verify no hallucinations occur
- Check error handling for edge cases

---

**Start by acknowledging your understanding and requesting the required files.**

```

---

Save this as `factshield_architecture.md` in your project root. The complete blueprint is now ready for your development team to begin implementation.