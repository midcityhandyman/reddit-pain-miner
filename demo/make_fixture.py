"""Regenerates fixtures/invoicing_software.json.

Every post and comment here is invented for this repository. Nothing is copied
from a real thread. The output uses the same payload shape the live client
parses ({"data": [...]}), so the fixture client replays it unchanged.
"""
import json
from pathlib import Path

SUB = "smallbiz_sample"
T0 = 1790000000

THREADS = [
    ("p001", "sample_user_01", 212, "Chasing late payments is eating my week",
     "I run a two person shop. I hate chasing late payments by hand every Friday. "
     "Payment reminders have to be sent manually for each overdue invoice and it takes forever. "
     "Anyone found something better?",
     [("sample_user_02", 88, "Same here. Sending payment reminders manually is so tedious, I waste hours every month on overdue invoices."),
      ("sample_user_03", 41, "Why can't the reminders for overdue invoices just go out on a schedule? I am tired of chasing late payments."),
      ("sample_user_04", 12, "We set up a spreadsheet and it works fine for us. No complaints so far."),
      ("sample_user_05", 30, "> Payment reminders have to be sent manually\nI wish there was a way to escalate overdue reminders after 30 days, chasing clients by hand is painful."),
      ("sample_user_06", 5, "How many clients do you have?")]),
    ("p002", "sample_user_07", 154, "Bank sync keeps breaking",
     "The bank sync in my invoicing software is broken again. It fails every few days and I have to reconnect the bank feed. "
     "Last month the sync created duplicate transactions and I spent a weekend cleaning them up.",
     [("sample_user_08", 67, "The bank feed sync is so buggy. Duplicate transactions every single week and reconciliation is a nightmare."),
      ("sample_user_02", 25, "Our bank sync stopped working after the last update and the bank connection still fails."),
      ("sample_user_09", 19, "I gave up and import bank statements manually now, which is tedious but at least there are no duplicate transactions."),
      ("sample_user_10", 8, "Which bank are you with? Ours has been stable."),
      ("sample_user_11", 33, "Frustrating that a broken bank sync is treated as normal, the feed fails and nobody tells you.")]),
    ("p003", "sample_user_12", 301, "They raised the price again",
     "My plan was 15 a month two years ago. They raised the price again and now charge per user. "
     "It is too expensive for a tiny team, and the price hike came with no new features.",
     [("sample_user_13", 120, "Per user pricing is a ripoff for small teams. We cancelled after the second price hike."),
      ("sample_user_01", 54, "Too expensive now. I hate that the cheaper plan was removed and the per user price doubled."),
      ("sample_user_14", 22, "Hidden fees on card payments too, the pricing page never mentions them."),
      ("sample_user_15", 9, "I am happy with the price honestly, it is great value for what we get."),
      ("sample_user_03", 37, "Looking for an alternative because the plan is overpriced and every price increase lands mid contract.")]),
    ("p004", "sample_user_16", 97, "Mobile app crashes when I scan receipts",
     "The mobile app crashes every time I scan a receipt on site. I lose the photo and have to scan the receipt again. "
     "Really frustrating when I am standing in a parking lot.",
     [("sample_user_17", 44, "Receipt scanning on the mobile app is useless, it crashes halfway through the upload."),
      ("sample_user_05", 18, "The app crashed on me three times today while scanning receipts. I can't trust the mobile app at all."),
      ("sample_user_18", 6, "Desktop works well for me, I just upload receipts at night."),
      ("sample_user_08", 27, "Scanned receipts come out blurry and the mobile app still crashes on older phones.")]),
    ("p005", "sample_user_19", 76, "Recurring invoices are too rigid",
     "I bill retainers monthly. There is no way to edit one recurring invoice without changing the whole series. "
     "I wish recurring invoices let me adjust a single month.",
     [("sample_user_20", 35, "Recurring invoices can't handle a mid month change, so I recreate the recurring series by hand each time."),
      ("sample_user_13", 21, "The recurring invoice template doesn't support custom line items, which is annoying for retainer clients."),
      ("sample_user_09", 11, "It is missing a pause button for recurring invoices, I had to delete the series for a client on break."),
      ("sample_user_21", 4, "What billing cycle do you use?")]),
    ("p006", "sample_user_22", 58, "Support took nine days to answer",
     "I opened a ticket about a wrong tax total. Support took nine days to reply and the answer was a link to the help page. "
     "I am still waiting for a real fix.",
     [("sample_user_11", 29, "Support never answers tickets in under a week. I am still waiting on a ticket from last month."),
      ("sample_user_17", 16, "Got no response from support for two weeks, then the ticket was closed without a reply."),
      ("sample_user_23", 7, "Chat support solved my issue in ten minutes, maybe it depends on the plan."),
      ("sample_user_20", 13, "Support is useless for tax questions, every ticket gets the same help page link.")]),
    ("p007", "sample_user_24", 133, "What do you dislike most about your invoicing software?",
     "Curious what bothers people day to day. For me the bank sync fails about once a week and I am sick of reconnecting the bank feed.",
     [("sample_user_25", 61, "Price. They raised the price twice this year and per user pricing is too expensive for a small team."),
      ("sample_user_26", 48, "Chasing late payments. I hate sending overdue payment reminders manually to every client."),
      ("sample_user_27", 26, "The mobile app crashes whenever I scan receipts, so I stopped scanning receipts on the phone."),
      ("sample_user_28", 15, "Support is useless, I am still waiting on a ticket about duplicate transactions from the bank sync."),
      ("sample_user_29", 10, "Nothing really, it works well for my needs.")]),
]


def build() -> dict:
    posts, comments = [], {}
    for n, (pid, author, score, title, body, replies) in enumerate(THREADS):
        posts.append({"id": pid, "subreddit": SUB, "title": title, "selftext": body, "author": author,
                      "score": score, "created_utc": T0 + n * 86400})
        comments[pid] = {"data": [
            {"id": f"c{pid[1:]}{i:02d}", "link_id": pid, "body": text, "author": who, "score": pts}
            for i, (who, pts, text) in enumerate(replies, start=1)]}
    return {"topic": "invoicing software", "note": "Synthetic recording. All text is invented.",
            "posts": {"data": posts}, "comments": comments}


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "fixtures" / "invoicing_software.json"
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out.name}")
