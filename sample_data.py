"""Ready-to-paste conversation examples for the Promise Tracker demo."""

from typing import Dict

SAMPLE_CONVERSATIONS: Dict[str, Dict[str, str]] = {
    "Sprint Retro & Incident Outage (Slack)": {
        "description": (
            "A production Redis outage retro with recovery actions, owners, "
            "deadlines, and an unanswered MFA access question."
        ),
        "transcript": """[09:02 AM] Maya: The checkout API was timing out for 18 minutes after the Redis failover. We need the incident notes and follow-ups before the customer review.
[09:04 AM] Jordan: I will write the incident timeline and post the RCA in Confluence by 1:00 PM today.
[09:06 AM] Maya: Thanks. Priya, can you check whether the retry patch is safe to release?
[09:08 AM] Priya: I will run the retry patch through staging and share the results before noon.
[09:10 AM] Leo: I have started reviewing the payment-service logs. I will attach the error-rate graph to the incident ticket by 11:30 AM.
[09:12 AM] Jordan: I can notify the affected customers after Maya approves the draft, no later than 3:00 PM.
[09:14 AM] Maya: Does anyone know who has the backup MFA device for the production Redis account? We need it before the next failover test.
[09:16 AM] Priya: I don't know where it is; I will ask IT and update the channel by 10:30 AM.""",
    },
    "Client Design & Scope Review (Teams)": {
        "description": (
            "A client review covering mobile design revisions, an Apple Pay "
            "decision, approval, and a scope question."
        ),
        "transcript": """[10:01 AM] Nina (Client): The new mobile checkout is close. Please make the address step shorter and move the order summary above the payment options.
[10:03 AM] Sam (Design): I will share revised checkout screens with the shorter address form by 4:00 PM tomorrow.
[10:05 AM] Nina (Client): Can we also include an Apple Pay toggle in this release, or would that change the estimate?
[10:07 AM] Alex (Product): I will check the Apple Pay scope with engineering and send Nina an impact estimate by Thursday morning.
[10:09 AM] Sam (Design): I have started updating the prototype. I will add the order summary placement and send a preview link before lunch today.
[10:11 AM] Nina (Client): Great. I will review the preview and send consolidated feedback by 5:00 PM tomorrow.
[10:13 AM] Alex (Product): I will update the project plan after we get the estimate approved.
[10:15 AM] Nina (Client): Who is approving the extra QA hours if Apple Pay is outside the original scope? We should settle that before adding it.""",
    },
    "Hackathon Project Planning (Discord)": {
        "description": (
            "A final-day hackathon plan with UI, integration, testing, and "
            "submission tasks plus an unresolved API quota blocker."
        ),
        "transcript": """[08:30 AM] @maya: Submission closes at 6 PM. Let's lock owners now and keep the demo path simple.
[08:32 AM] @ravi: I will finish the task-board empty state and loading animation by 11:00 AM.
[08:34 AM] @chen: The extraction endpoint is wired up; I'm testing the response parser now. I will fix any JSON parsing bugs before 1 PM.
[08:36 AM] @maya: I will write the project README and deployment steps and push them by 2:00 PM.
[08:38 AM] @ravi: Once the endpoint is stable, I will run the full demo flow and post a screen recording by 3:30 PM.
[08:40 AM] @chen: I will add the sample transcript and test the quote highlighting before 2:30 PM.
[08:42 AM] @maya: Does anyone know if our Gemini API quota resets before the judging demo? The current key started returning rate-limit errors.
[08:44 AM] @ravi: I don't have access to the billing console. I'll ask the organizer and report back by 9:30 AM.
[08:46 AM] @chen: If quota is still blocked, who can provide a backup key?""",
    },
}
