# Task 3 — Executive Email: Expectation Management

> Context: at the phase-1 review, the BU executive said the AI is still wrong 10–15% of the time, that it must be 100% correct or the work won't be accepted, and that staff must not have to reformat documents ("AI must read messy files").
> Below: the Thai email I would send (the BU is Thai), then the same email in English.

---

## ฉบับภาษาไทย

**เรื่อง:** แผนยกระดับความถูกต้องของ AI Knowledge Agent และเกณฑ์ตรวจรับที่วัดผลได้

เรียน คุณ[ชื่อผู้บริหาร]

ขอบคุณสำหรับ feedback ในที่ประชุมครับ ผมเห็นด้วยว่าพนักงานต้องได้คำตอบที่เชื่อถือได้ และไม่ควรต้องเสียเวลาจัดรูปแบบเอกสารใหม่ และเข้าใจครับว่าการลงทุนครั้งนี้ต้องคุ้มค่า จึงขอเสนอแนวทาง 5 ข้อดังนี้ครับ

1. **สิ่งที่เรารับประกันได้ 100% คือ "ไม่มีคำตอบไหนที่ไม่มีเอกสารอ้างอิง"**
    ระบบบัญชีเป็นแบบ Deterministic คือให้ผลตายตัวเพราะคำนวณตามสูตร แต่ AI เป็นแบบ Probabilistic ต้องตีความภาษาคน ซึ่งคล้ายพนักงานใหม่ที่เก่งมากแต่ยังพลาดได้ (เช่นเดียวกับการถาม HR หรือค้นเอกสารเองในปัจจุบัน) สิ่งที่เราควบคุมได้คือ ทุกคำตอบต้องแนบเอกสารอ้างอิงให้ตรวจสอบได้ทันที (บังคับด้วยระบบ ไม่ใช่แค่ขอให้ AI ทำ) และถ้าระบบไม่มั่นใจ จะตอบว่า "ไม่พบข้อมูล" พร้อมส่งต่อเจ้าหน้าที่ แทนการเดา

2. **แบ่งคำถามตามระดับความเสี่ยง**
    - **สูง** (เงินเดือน ภาษี กฎหมาย การอนุมัติเงิน): AI ร่างคำตอบพร้อมอ้างอิง แต่ **เจ้าหน้าที่ยืนยันก่อนส่ง** (Human-in-the-loop) หรือแสดงเฉพาะข้อความต้นฉบับจากระเบียบ
    - **ปานกลาง**: ตอบทันทีพร้อมอ้างอิง และสุ่มตรวจทุกสัปดาห์
    - **ต่ำ** (FAQ ทั่วไป): ตอบอัตโนมัติ

    เป้าหมายคือ **ไม่มีคำตอบผิดในกลุ่มความเสี่ยงสูงถึงมือพนักงานเลย**

3. **แก้ 10–15% อย่างเป็นระบบ ไม่ใช่สุ่มแก้**
    เราจะจำแนกคำตอบที่ผิดทุกข้อว่าเกิดจาก (ก) เอกสารไม่มีหรือล้าสมัย (ข) ระบบค้นไม่เจอ หรือ (ค) AI สรุปผิด แต่ละสาเหตุมีวิธีแก้ต่างกัน เช่น (ก) แก้ที่เอกสารต้นทาง และ (ค) เพิ่มการตรวจคำตอบอัตโนมัติ พร้อมรายงานความคืบหน้าให้ BU ทุกสัปดาห์

4. **พนักงานไม่ต้องจัดรูปแบบเอกสารใหม่**
    ระบบมีขั้นตอนทำความสะอาดเอกสารอัตโนมัติ ในต้นแบบเราวัดผลแล้วว่าอ่านข้อความภาษาไทยจาก PDF ได้ตรง 100% หลังผ่านขั้นตอนนี้ ส่วนไฟล์สแกนจะเพิ่ม OCR และระบบจะแจ้งเจ้าของเอกสารเฉพาะไฟล์ที่อ่านไม่ได้จริงเท่านั้น

5. **เสนอเกณฑ์ตรวจรับที่วัดผลได้** แทน "100% ทุกคำถาม"
    ใช้ชุดคำถามทดสอบประมาณ 300 ข้อจากคำถามจริง ที่ BU ร่วมคัดเลือกและเฉลย
    - กลุ่มความเสี่ยงสูง: **0 คำตอบผิดถึงมือพนักงาน** (ผ่านการยืนยันโดยเจ้าหน้าที่)
    - ภาพรวม: ถูกต้อง **≥ 95%** และ **ทุกคำตอบมีแหล่งอ้างอิง**
    - เมื่อเอกสารไม่ครอบคลุมคำถาม: ตอบ "ไม่พบข้อมูล + ส่งต่อ" **100%** แทนการเดา

ขอนัดหารือ 30 นาทีในสัปดาห์หน้า เพื่อร่วมกำหนดชุดคำถามทดสอบและหมวดความเสี่ยงครับ

ขอแสดงความนับถือ  
หฤษฏ์ ศิริเทพ

---

## English version

**Subject:** Plan to raise AI Knowledge Agent accuracy, with measurable acceptance criteria

Dear [Executive name],

Thank you for the feedback in our review. I agree that staff must get answers they can trust, and they shouldn't have to reformat documents. I also understand this investment has to pay off. Here is what I propose:

1. **What we can guarantee 100%: no answer without a source.**
    An accounting system is deterministic: it gives the same result every time because it follows a formula. An AI is probabilistic: it interprets human language, more like a very capable new employee who can still make mistakes (as people do today when they ask HR or search documents themselves). What we *can* control: every answer shows its source document so it can be checked instantly (enforced in code, not just asked of the AI), and when the system isn't confident it says "I couldn't find this" and hands the question to a person, instead of guessing.

2. **Tier questions by risk.**
    - **High** (salary, tax, legal, money approvals): the AI drafts an answer with sources, but **a staff member confirms it before it's sent** (human-in-the-loop), or the AI shows only the exact policy text.
    - **Medium**: answered instantly with sources, spot-checked weekly.
    - **Low** (general FAQ): fully automatic.

    Goal: **zero wrong answers reach employees in the high-risk tier.**

3. **Fix the 10–15% systematically, not by trial and error.**
    We classify every wrong answer by cause: (a) the document is missing or outdated, (b) the search didn't find it, or (c) the AI summarised it wrongly. Each cause has its own fix: (a) is fixed at the source document, (c) with automatic answer checks. Weekly progress report to the BU.

4. **No reformatting for staff.**
    The system has an automatic document-cleaning step. In the prototype we measured 100% accurate Thai text extraction from PDFs after this step. Scanned files will get OCR, and only files that truly can't be read are flagged, to the document owner, not to every employee.

5. **Measurable acceptance criteria** instead of "100% on every question".
    A test set of ~300 real questions, chosen and answered by the BU:
    - High-risk tier: **0 wrong answers reach employees** (via staff confirmation)
    - Overall: **≥ 95% correct**, and **every answer cites a source**
    - When the documents don't cover a question: **100% "not found + hand-off"**, never a guess

Could we book 30 minutes next week to agree on the test set and the risk categories together?

Best regards,  
Harit S.

---

*Why this structure:* it agrees with the goal before reframing it (trust, no reformatting). It turns "100% accuracy", which a probabilistic system can't promise, into "100% never confidently wrong", which we *can* promise and enforce. Human review is placed only where the risk justifies its cost. It answers the "messy files" point with evidence from the prototype, and it ends with a concrete next step that makes the BU co-owner of the acceptance test.
