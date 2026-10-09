# Job Application Assistant

A small learning project for preparing job application inputs. It provides a
browser-based form for a job posting URL, retrieved or pasted job text, and
CV/profile text.

## Run locally

Use Python 3.12 or newer, as specified in the project roadmap. From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local address printed by Streamlit in your browser.

## Save your profile locally

Copy `profile.example.txt` to `profile.txt` in this folder, then replace the
example sections with your own CV/profile information. The app loads
`profile.txt` into the profile field when it starts. You can still edit the
field for an individual review, but edits in the form are not written back to
the file.

The local `profile.txt` is ignored by Git so personal CV information is not
accidentally included in a commit. Do not put real CV details in
`profile.example.txt`, which is a shareable template.

## Configure Gemini

Create or select a Google AI Studio project and create a Gemini API key at
[Google AI Studio API keys](https://aistudio.google.com/apikey). The app uses
the `gemini-flash-latest` model and requests structured JSON for job requirements
and CV-match reports.

In the same macOS Terminal session where you will run Streamlit, enter the API
key at the hidden prompt so it is not written into the shell command history:

```sh
read -s "GEMINI_API_KEY?Gemini API key (input hidden): "
export GEMINI_API_KEY
printf '\n'
```

Keep the key private. Do not put it into source code, `README.md`, or a
committed file. Run `streamlit run app.py` from that same terminal so the app receives the
environment variable. **Analyze job requirements** sends only the job-posting
text to Gemini. **Assess CV match** sends both the posting and CV/profile text
to Gemini to return a qualitative fit assessment, evidence-backed strengths,
and potential gaps. Use the match action only if you are comfortable sharing
that information with the API provider. Check the current Gemini API pricing,
quota, and data-use terms for your account before sending real job data; API
availability and cost depend on your account and usage.

## What this first step does

- Fetches and extracts text from public HTTP/HTTPS job posting pages, or accepts
  a pasted job description when retrieval is unavailable.
- Can extract the job title, responsibilities, required and preferred skills,
  technologies, and experience requirements using Gemini.
- Can compare CV/profile evidence against a job posting and show a qualitative
  fit assessment, strengths, gaps, and suggested next steps.
- Loads profile text from `profile.txt` when available, or lets you paste it.
- Requires CV/profile text when reviewing inputs.
- Checks URL scheme, destination addresses, redirect targets, response size,
  and request timeout before showing fetched text for review.
- Shows a brief confirmation and character counts after you select **Review
  inputs**.

The app fetches a page only after you choose **Fetch posting**. Gemini is called
only after you choose **Analyze job requirements** or **Assess CV match**. AI
extraction and match assessments may omit or misinterpret details; review all
results against the original posting and your actual experience. The app does
not persist submitted text or submit applications. HTML extraction is
best-effort; job sites that render content with JavaScript or restrict
automated access may require you to paste the description. Respect each site's
terms and access restrictions.

This is a local learning MVP, not a hardened public URL-fetching service. Do not
expose it to untrusted users without additional network-level egress controls
and deployment security review.

## Learning exercise

Open `models.py` and add one additional posting field, then update the prompt
and tests to confirm Gemini returns it in the validated result.

## Next step

Add evidence citations and configurable match-assessment criteria.
