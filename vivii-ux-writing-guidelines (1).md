# ViVii — UX Writing Guidelines

> Draft 1 | April 2026

---

## Mục đích

Document này hướng dẫn cách viết UX copy cho ViVii — từ landing page, in-app UI, đến notifications. Dành cho tất cả mọi người trong team: dev, design, PM, marketing.

**Cách dùng:**
- Đọc phần Voice Summary + Tone Dimensions để hiểu ViVii "nói" kiểu gì
- Tra bảng Do/Don't khi viết copy
- Check phần Applying by Context cho từng loại surface
- Chạy Quick Checklist trước khi ship

**Source of truth cho brand personality:** [vivii-brand-identity-keywords.md](vivii-brand-identity-keywords.md)

---

## Voice Summary

ViVii nói chuyện như **một người bạn rất sâu nhưng không bao giờ tỏ ra sâu** — kiểu người biết tại sao "cookout" không phải chỉ là BBQ, nhưng sẽ giải thích bằng cách nói "trust me, đừng đến tay không."

Cụ thể hơn:
- **Ngắn hơn bạn nghĩ.** Nếu cắt được 1 từ mà nghĩa không đổi — cắt.
- **Nói như đang chat, không phải đang thuyết trình.** Avoid corporate voice.
- **Có quan điểm.** Không trung lập đến mức nhạt. ViVii có opinion.
- **Không giải thích joke.** Nếu phải giải thích, viết lại.

---

## Tone Dimensions

4 tones dưới đây không phải 4 chế độ riêng biệt — chúng blend với nhau. Tuỳ context mà 1-2 tone sẽ dominant hơn.

| Tone | Khi nào dùng | Ví dụ |
|---|---|---|
| **Deadpan** — Nói điều nghiêm túc theo cách buồn cười, không cần giải thích | Headlines, empty states, CTAs | *"You've been studying English for 10 years. Still need subtitles."* |
| **Sarcastic** — Có quan điểm, châm biếm nhẹ. **Dùng tiết chế** — quá nhiều sẽ thành toxic | So sánh với competitor (gián tiếp), upgrade prompts | *"Your vocabulary flashcards are lonely. You haven't visited in 12 days."* |
| **Casually profound** — Insight sâu nhưng deliver nhẹ nhàng, như đang tám chuyện | Culture explanations, onboarding, feature descriptions | *"Language is just the door. Culture is the house."* |
| **Chaotic-good** — Năng lượng hỗn độn nhưng có mục đích. Unexpected, không random | Achievements, streaks, easter eggs, social sharing | *"New stamp unlocked: American Dining. You now understand why tipping 20% isn't optional."* |

### Khi nào KHÔNG dùng tone mạnh

- **User đang bị lỗi hoặc mất data** → giảm sarcastic, tăng clarity
- **Onboarding step đầu tiên** → chưa build trust, chưa nên quá edgy
- **Legal / privacy / payment** → straight, clear, no jokes

---

## Voice Chart — ViVii vs. Others

Bảng này giúp team hình dung nhanh ViVii đứng ở đâu so với các brand quen thuộc.

| Dimension | **Duolingo** | **Headspace** | **Notion** | **ViVii** |
|---|---|---|---|---|
| **Overall tone** | Playful, cheerful, guilts you into learning | Calm, gentle, reassuring | Minimal, functional, dry | Witty, sharp, deadpan |
| **Nói với user kiểu** | Encouraging parent | Meditation guide | Efficient colleague | That one friend who knows too much about everything |
| **Motivate user** | "Great job! Keep it up!" | "You showed up. That's enough." | (Doesn't really motivate) | "47 episodes in. Might as well learn something." |
| **Handle lỗi** | "Oops! Something went wrong" | "Let's take a breath and try again" | "Something went wrong. Try again." | "That didn't work. Not your fault. Probably." |
| **Celebrate success** | Confetti + "Amazing!!!" | "Well done. Be proud." | Checkbox checked. Done. | "You understood a meme without Googling it. Growth." |

---

## Do / Don't

| # | Principle | Do | Don't | Tại sao |
|---|---|---|---|---|
| 1 | **Be short** | "Tap any word. Get it." | "Tap on any word in the transcript to see a detailed explanation of its meaning" | Mỗi từ thừa = 1 giây user không cần mất |
| 2 | **Use real examples, not abstractions** | "Pull up" doesn't mean pull up." | "Learn vocabulary in real-world context" | Cụ thể tạo trust. Trừu tượng tạo hoài nghi |
| 3 | **Have an opinion** | "Subtitles are a crutch. We're the rehab." | "We help you reduce your dependency on subtitles" | ViVii không trung lập — neutral = boring |
| 4 | **Be self-aware, not self-important** | "Yeah, we're a learning app. A good one." | "The revolutionary language learning platform" | User ghét brands tự phong tước hiệu |
| 5 | **Don't explain the joke** | "12-day streak. More committed than your last relationship." | "12-day streak! That's really impressive, like how you'd be committed to a relationship!" | Nếu cần giải thích = không funny |
| 6 | **Internet-native, not internet-try-hard** | "You're out of imports. Upgrade or wait 23 days. We'd recommend not waiting." | "OMG you've used all your imports!!! Upgrade NOW to keep learning!!! " | Dùng energy của internet, không cosplay internet |
| 7 | **Show, don't tell emotions** | "New stamp: Soul Food. You get it now." | "Congratulations! You've earned a new cultural stamp! We're so proud of you!" | ViVii doesn't over-celebrate. Let the achievement speak |
| 8 | **Clarity first, cleverness second** | Error: "Link not supported yet. Try YouTube or Spotify." | Error: "Hmm, we don't speak that language yet." | Khi user cần help, đừng sacrifce clarity cho wit |
| 9 | **Respect the user's intelligence** | "3 layers: meaning, context, culture." | "Our innovative 3-layer system helps you understand words better than ever before" | User biết mình cần gì. Không cần sell |
| 10 | **No filler words** | "Your library is empty. Paste a link." | "It looks like your library is empty right now! Why not get started by pasting a link?" | "It looks like", "Why not", "Get started" = noise |

---

## Applying by Context

### Marketing / Landing Page

- Tone dominant: **Deadpan + Casually profound**
- Headlines ngắn, punch mạnh. Dùng contrast (kỳ vọng vs. thực tế) để tạo hook
- Không oversell. Không dùng "revolutionary", "game-changing", "like never before"
- CTA có personality: prefer "Start actually understanding" over "Sign up now"

### In-App UI (buttons, labels, tooltips)

- Tone dominant: **Deadpan** (nhẹ)
- **Clarity là ưu tiên #1.** Wit chỉ khi không hy sinh comprehension
- Labels: ngắn, verb-first. "Add to vocab" not "Add this word to your vocabulary bank"
- Tooltips: 1 câu. Nếu cần nhiều hơn, chuyển sang help doc

### Notifications & Streaks

- Tone dominant: **Chaotic-good + Sarcastic** (tiết chế)
- Không guilt-trip quá nặng. Sarcastic nhẹ, không passive-aggressive
- Vary copy — đừng lặp cùng 1 message. User sẽ numb
- Streak messages nên escalate theo số ngày (ngày 3 khác ngày 30 khác ngày 100)

### Error States & Empty States

- Error: **Clarity first.** Nói rõ chuyện gì xảy ra + user làm gì tiếp. Tone nhẹ, không forced humor
- Empty state: **Đây là cơ hội tốt cho personality.** User không bị stress → có thể dùng deadpan/wit
- Loading: Ngắn. Không cần funny. Skeleton UI nói nhiều hơn copy

---

## Quick Checklist

Trước khi ship bất kỳ UX copy nào, chạy qua 6 câu này:

- [ ] **Cắt được từ nào không?** — Đọc lại, bỏ mọi từ không mang nghĩa
- [ ] **Nghe như đang nói chuyện hay đang viết slide?** — Nếu slide, viết lại
- [ ] **Có opinion không?** — Nếu brand nào cũng nói được câu này, chưa đủ ViVii
- [ ] **User có hiểu ngay không?** — Wit không bao giờ được đánh đổi clarity
- [ ] **Có đang oversell không?** — Bỏ "revolutionary", "amazing", "best ever"
- [ ] **Đọc to lên có cringe không?** — Nếu có, viết lại

---

*Guideline này là living document — update khi team có thêm learnings từ user feedback.*
