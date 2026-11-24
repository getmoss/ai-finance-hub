---
name: moss-software-spend-surface
description: "Software Spend Snapshot Surface. Scans a company's transaction list to identify which transactions are software or SaaS spend, since that spend routinely gets lost across different expense accounts, mis-booked under a vague note, or simply not recognised because the vendor name is unfamiliar. Consolidates vendor name variants into one canonical vendor and adds a one line description of what each tool is. Delivered as a table in chat first, with an offer to export to Excel or CSV. Use whenever someone wants to know what software or SaaS tools a company is actually paying for, wants to find spend hiding in the wrong account, or asks things like \"what software are we paying for\", \"find our SaaS spend\", or \"scan our transactions for software costs\"."
---

> **Version:** v2.16 — added `normalize.py` input normalisation layer. Pipeline now accepts DATEV xlsx, generic xlsx/csv, and text-based PDFs in addition to DATEV. Scanned PDFs trigger a limitation notice. Interactive column mapping for unrecognised formats. Taxonomy: 640 patterns (unchanged from v2.14).

# Software Spend Snapshot Surface

You are helping someone find software and SaaS spend that's scattered across a company's transactions, rather than sitting cleanly in one place. Most companies don't have a single account that captures all of it. Instead, software is often recorded inconsistently: a tool bought by one team goes through as a card charge, another gets booked to general IT costs, and a third never gets coded as software at all because whoever processed the invoice didn't recognize the vendor and filed it as a generic expense. On top of that, subscription costs are spread across different billing cadences, with some tools billed monthly, annually, prepaid in advance, or recognized through accruals. Together, inconsistent accounting treatment and varying billing schedules make it difficult to maintain a complete, reliable view of total software spend. This skill surfaces the software spend hiding across all of that.

---

## Conversation flow

### Step 1 — Welcome

Start immediately with the welcome message. Do not check for uploaded files, verify whether a file exists, or mention file upload status before displaying the welcome message.

Open with:

> **Find the software spend hiding in your books.**
>
> Upload a transaction export from your accounting system and this skill will surface the software, SaaS, and AI vendors it can find, with a short plain-English description of what each tool does.
>
> The goal is the first investigation view: which tools are actually showing up in your transactions, even when they were booked under accounts nobody would think to check, or appeared in months where nobody was looking for them.
>
> **How to use this skill:**
>
> **1. Upload your transaction list**
> Export your transactions from your accounting system, for example DATEV, Xero, QuickBooks, or NetSuite.
> Supported formats: **Excel (xlsx), CSV, and text-based PDF** (bank statements where the text is selectable). Scanned PDFs are not supported — export as text PDF or CSV instead.
> Ideally upload a full year. Software spend often hides outside the software account, and some tools only show up once a year, through prepayments, accrual releases, or vague card transactions.
>
> **2. Let the skill do the first pass**
> The skill scans the file, looks for software, SaaS, and AI vendors, and reviews unclear booking text. If something important is missing or unclear, it may ask a short follow-up question.
>
> **3. Review the vendor table**
> You will get an alphabetically sorted table of vendors, with a short description of what each tool does. If the skill is unsure about a vendor, it will say so before the table.
>
> **4. Export the result**
> After the table, you can ask for the output as Excel, CSV, or Google Sheets-ready format.
>
> Upload your transaction list and we will start the first investigation.

Do not ask what period the file covers or what to focus on. Auto-detect the period from the data and run on everything.

### Step 2 — Something to read while it runs

Before starting the extraction, always display the following fixed waiting message. Do not change, rotate, or personalize it

What is happening now

The skill is reading through your transaction export and looking for software, SaaS, and AI vendors that may not sit neatly in one software account.
It checks known vendor names, reviews messy booking text, removes obvious non-software noise, and flags cases where the vendor is uncertain instead of forcing a confident answer.

No magic. Just a structured first pass through the kind of file finance usually has to investigate manually.

CRITICAL FORMATTING RULE: the three parts above are three separate paragraphs. When you output this message in the chat, you must put a full blank line (an empty line, i.e. two line breaks) between each of the three parts. Do not put them on consecutive lines with only a single line break between them, that renders as one squashed block with no visible gap. Each paragraph needs its own clear vertical space above and below it.

Then move straight into the extraction, no lingering transition needed.

### Step 3 — Extract and cross-check vendor names

**FIRST: find the skill scripts. This is mandatory before doing anything else.**

Run this check:
```
python3 -c "
import os, glob
candidates = [
    'scripts/extract_candidates.py',
    '/mnt/skills/user/software-spend-snapshot-surface-v2/scripts/extract_candidates.py',
]
candidates += glob.glob('/mnt/skills/**/extract_candidates.py', recursive=True)
candidates += glob.glob(os.path.expanduser('~/skills/**/extract_candidates.py'), recursive=True)
found = next((p for p in candidates if os.path.exists(p)), None)
if found:
    print('MODE_A:' + os.path.dirname(found))
else:
    print('MODE_B')
"
```

- If it prints `MODE_A:/some/path` → **Mode A (scripted)**. Set `SKILL_DIR` to that path and use it as prefix for all script calls below. Example: `python3 /mnt/skills/user/software-spend-snapshot-surface-v2/scripts/extract_candidates.py ...`
- If it prints `MODE_B` → **Mode B (in-context)**. No scripts available. Follow Mode B below.

**Do not assume or guess the mode. Run the check.**

---

#### Mode A — scripted pipeline (Cowork / Projects)

**3a — Normalise the input file (script).**

Run `normalize.py` first. It detects the file format and produces a standard
`normalised.csv` with columns `[description, amount, date]` for the rest of the pipeline.

```
python3 $SKILL_DIR/normalize.py --input <file> [--output normalised.csv]
```

**What happens depending on the file:**

| Input | Behaviour |
|---|---|
| DATEV xlsx/csv (column "Buchungstext" present) | Auto-detected, no questions asked |
| Generic xlsx/csv (known column names) | Auto-detected silently |
| Generic xlsx/csv (unknown columns) | Script prints the column list and asks the user 3 questions interactively |
| Text-based PDF | Tables extracted via pdfplumber; same detection logic as xlsx/csv |
| Scanned PDF | Prints a limitation notice and exits — do not continue the pipeline |
| Unsupported format | Prints a limitation notice and exits — do not continue the pipeline |

**Scanned PDF / unsupported format — what to tell the user:**

If `normalize.py` exits with a limitation notice, relay the message to the user as-is and
stop. Do not attempt to work around it. The user needs to re-export in a supported format.

**Interactive column mapping — how to handle it:**

If the script asks for column input (generic file with unrecognised headers), show the user
the column list the script printed and ask them to answer in the chat. Then pass their
answers back to the running script, or re-run `extract_candidates.py` with `--column <name>`
directly using the column name the user identified.

**3b — Extract candidates (script).**
```
python3 $SKILL_DIR/extract_candidates.py --input normalised.csv --column description --output candidates.csv
```
Deterministically cleanses each value (payment-processor prefixes like "PAYPAL *"/"Stripe *",
invoice/reference numbers, dates, legal-entity suffixes), deduplicates case-insensitively,
counts transactions per candidate, and sorts alphabetically.

**3c — Pass 1, taxonomy matching (script).**
```
python3 $SKILL_DIR/match_taxonomy.py --candidates candidates.csv --taxonomy $SKILL_DIR/../references/vendor_taxonomy.csv
```
Outputs: `matched.csv`, `excluded.csv`, `unmatched.csv`.

**3d — Pass 2 pre-filter (script).**
```
python3 $SKILL_DIR/prefilter_unmatched.py \
    --unmatched unmatched.csv \
    --matched matched.csv \
    --priority pass2_priority.csv \
    --residual pass2_residual.csv
```
Removes noise and splits unmatched into priority (~500 rows with software signals) and residual.

**⚠️ Guardrail — mandatory before continuing.**

If any script in steps 3b–3d prints a message containing "LOW", "Do NOT present", "coverage is", or "stopped early" — stop immediately. Do NOT present results. Tell the user:

> "The analysis ran into an issue: [copy the exact warning message here]. I am stopping rather than showing you a result that may be incomplete. Please let me know how you'd like to proceed."

Do not override this. Do not decide the warning is a false positive. Do not present partial results as complete.

**3e — Pass 2 LLM review.**
Work through `pass2_priority.csv` fully first — print all rows in batches of 300, decide
each row, then continue. NEVER stop mid-file. Then do the same for `pass2_residual.csv`.
Record every include in `pass2_includes.csv` with columns:
`vendor, description, source_candidate, unverified`.

**Canonical naming rule (mandatory).** The `vendor` field must be the vendor's name exactly
as it appears in the `candidate` or `sample_original` column — the clearest, most
recognisable form. Do NOT invent a cleaner name, do NOT translate to English, do NOT add
or remove suffixes. If the candidate is `APPLE.COM/DE` → vendor is `APPLE.COM/DE`, not
`Apple`. If the candidate is `G2.com` → vendor is `G2.com`, not `G2`. If sample_original
shows `CharlieHR` → vendor is `CharlieHR`, not `Charlie HR`. Use `sample_original` to
disambiguate when the cleansed candidate is a truncated fragment.

**Anti-fabrication rule (mandatory).** Every vendor you add MUST trace to a concrete row in
`unmatched.csv`. Never add vendors from memory, prior conversations, or general knowledge of
"what companies like this usually buy".

**3f — Build final table (script).**
```
python3 $SKILL_DIR/build_table.py --matched matched.csv --pass2 pass2_includes.csv \
    --output final_table.csv --priority pass2_priority.csv
```
Do not present the table until the exhaustion check passes (≥80% of high-frequency candidates
covered) or you have genuinely exhausted both priority and residual files.

**If the exhaustion check warns coverage is LOW:** you MUST continue Pass 2 from where you
stopped. Print the next batch of rows, decide them, add includes to pass2_includes.csv,
re-run build_table. Repeat until coverage ≥80% or all rows are exhausted.

---

#### Mode B — in-context pipeline (standard claude.ai chat)

Scripts are not available. You will do Pass 1 and Pass 2 yourself using the taxonomy embedded
below. Results are slightly less deterministic than Mode A but follow the same rules.

**3a — Identify the merchant column (you).** Same as Mode A step 3a.

**3b — Extract unique merchant strings (you, via pandas/openpyxl).**
Read the merchant column, split each value on ";", strip payment-processor prefixes
(PAYPAL *, Stripe *, SumUp *, SQ *, AMZN Mktp *), remove invoice numbers, dates,
and legal suffixes (GmbH, Ltd, Inc, B.V., AG). Deduplicate case-insensitively.
Count occurrences (tx_count). Sort by tx_count descending.

Write the result as a working list in memory: `[(candidate, sample_original, tx_count), ...]`

**3c — Pass 1: match against the embedded taxonomy (you).**

The taxonomy below has 481 include patterns and 38 exclude patterns.
Format: `S:pattern=Canonical` (substring match) or `E:pattern=Canonical` (exact match).
Apply first-match-wins in listed order. A match → vendor goes to output table.
An exclude match → dropped silently. No match → goes to Pass 2.

```
S:openai=OpenAI
S:anthropic=Anthropic
S:claude=Anthropic
S:elevenlabs=ElevenLabs
S:perplexity=Perplexity
S:midjourney=Midjourney
S:heygen=HeyGen
S:higgsfield=Higgsfield
S:openrouter=OpenRouter
S:gamma.app=Gamma
S:mistral=Mistral
E:xai=xAI
S:klingai=KlingAI
S:runway=Runway
S:synthesia=Synthesia
E:manus=Manus
S:langdock=Langdock
S:granola=Granola
S:fireflies=Fireflies
S:wispr=Wispr
E:deepl=DeepL
S:deepl =DeepL
E:www.deepl.com=DeepL
S:grammarly=Grammarly
S:descript=Descript
E:suno=Suno
E:cursor=Cursor
S:lovable=Lovable
S:replit=Replit
S:windsurf=Windsurf
S:amazon web services=Amazon Web Services
S:google cloud=Google Cloud
S:hetzner=Hetzner
S:digitalocean=DigitalOcean
S:cloudflare=Cloudflare
E:vercel=Vercel
E:railway=Railway
E:netlify=Netlify
E:supabase=Supabase
S:ovhcloud=OVHcloud
S:scaleway=Scaleway
S:github=GitHub
S:gitlab=GitLab
S:jetbrains=JetBrains
S:atlassian=Atlassian
S:sentry=Sentry
S:docker=Docker
S:sonarsource=SonarSource
S:sonarcloud=SonarSource
S:browserstack=BrowserStack
S:twilio=Twilio
S:mailgun=Mailgun
S:ngrok=Ngrok
S:datadog=Datadog
S:postman=Postman
S:uptimerobot=UptimeRobot
S:parallels=Parallels
S:apify=Apify
S:firecrawl=Firecrawl
S:solarwinds=SolarWinds
S:teamviewer=TeamViewer
S:auth0=Auth0
S:tailscale=Tailscale
S:fivetran=Fivetran
S:messagebird=MessageBird
S:bird.com=MessageBird
S:elastic=Elastic
S:new relic=New Relic
S:newrelic=New Relic
S:pagerduty=PagerDuty
S:posthog=PostHog
S:circleci=CircleCI
S:grafana=Grafana Labs
S:mongodb=MongoDB
S:mapbox=Mapbox
S:algolia=Algolia
S:contentful=Contentful
S:lokalise=Lokalise
S:ninjaone=NinjaOne
S:kaseya=Kaseya
S:better stack=Better Stack
S:betterstack=Better Stack
S:lansweeper=Lansweeper
S:slack=Slack
E:zoom=Zoom
S:zoomvideo=Zoom
S:zoom.com=Zoom
S:zoom.us=Zoom
S:microsoft=Microsoft
S:gsuite=Google Workspace
S:notion=Notion
S:miro=Miro
E:loom=Loom
S:dropbox=Dropbox
S:wetransfer=WeTransfer
S:calendly=Calendly
S:superhuman=Superhuman
S:riverside=Riverside
S:aircall=Aircall
S:codetwo=CodeTwo
S:demodesk=Demodesk
S:monday=Monday.com
S:asana=Asana
S:linear.app=Linear
S:trello=Trello
S:clickup=ClickUp
S:figma=Figma
S:adobe=Adobe
S:autodesk=Autodesk
S:capcut=CapCut
S:envato=Envato
S:artlist=Artlist
S:lucid=Lucid Software
S:framer=Framer
S:vimeo=Vimeo
S:myfonts=MyFonts
S:font awesome=Font Awesome
S:pitch.com=Pitch
S:screenstudio=Screen Studio
S:epidemic sound=Epidemic Sound
S:mobbin=Mobbin
S:frame.io=Frame.io
S:salesforce=Salesforce
S:zoho=Zoho
S:hubspot=HubSpot
S:pipedrive=Pipedrive
S:clay labs=Clay
S:apollo.io=Apollo.io
S:lemlist=Lemlist
S:lusha=Lusha
S:phantombuster=PhantomBuster
S:linkedin%recruiter=LinkedIn Recruiter
S:linkedinprec=LinkedIn Recruiter
S:linkedin=LinkedIn
S:mailchimp=Mailchimp
S:klaviyo=Klaviyo
S:sendinblue=Sendinblue
S:semrush=Semrush
S:ahrefs=Ahrefs
S:typeform=Typeform
S:mailjet=Mailjet
S:x corp=X (Twitter)
S:linktree=Linktree
S:bitly=Bitly
S:screaming frog=Screaming Frog
S:jotform=Jotform
S:contentsquare=Contentsquare
S:customer.io=Customer.io
S:customerio=Customer.io
S:reddit=Reddit
S:activecampaign=ActiveCampaign
S:reviews.io=Reviews.io
S:sistrix=Sistrix
S:channable=Channable
S:trustpilot=Trustpilot
S:chatarmin=Chatarmin
S:stackadapt=StackAdapt
S:personio=Personio
S:join.com=Join.com
S:leapsome=Leapsome
S:hibob=HiBob
E:bob=HiBob
S:bob b v=HiBob
S:bamboohr=BambooHR
S:xero=Xero
S:easybill=Easybill
S:sevdesk=Sevdesk
S:getmyinvoices=GetMyInvoices
S:chargebee=Chargebee
S:xentral=Xentral
S:odoo=Odoo
S:revenuecat=RevenueCat
S:1password=1Password
S:bitwarden=Bitwarden
S:lastpass=LastPass
S:proton=Proton
S:vanta=Vanta
S:seon=SEON
S:zendesk=Zendesk
S:intercom=Intercom
S:freshworks=Freshworks
S:gorgias=Gorgias
S:zapier=Zapier
S:make.com=Make
S:n8n=n8n
S:airtable=Airtable
S:webflow=Webflow
E:bubble=Bubble
S:bubble =Bubble
S:godaddy=GoDaddy
S:ionos=IONOS
E:wix=Wix
S:wix.com=Wix
S:squarespace=Squarespace
S:sqsp=Squarespace
S:united domains=United Domains
S:elementor=Elementor
S:eurodns=EuroDNS
S:maxcluster=MaxCluster
S:docusign=DocuSign
S:pandadoc=PandaDoc
S:cookiebot=Cookiebot
S:usercentrics=Usercentrics
S:borlabs=Borlabs
S:caya=Caya
S:shopify=Shopify
S:udemy=Udemy
S:metabase=Metabase
S:tableau=Tableau
S:looker=Looker
S:mixpanel=Mixpanel
S:amplitude=Amplitude
S:snowflake=Snowflake
S:getmoss=Moss
E:moss=Moss
S:google ads=Google Ads
S:google *ads=Google Ads
S:googleadwords=Google Ads
S:google*ads=Google Ads
S:facebk=Meta Ads
S:facebook ads=Meta Ads
S:meta ads=Meta Ads
S:linkedin ads=LinkedIn
S:chatgpt=OpenAI
S:klarna=Klarna
S:canva=Canva
S:11x=11x
S:payhawk=Payhawk
S:complyadvantage=ComplyAdvantage
S:bitdefender=Bitdefender
S:united-domain=united-domains
S:payrnet=PayrNet
S:railsr=Railsr
S:rapyd=Rapyd
S:airwallex=Airwallex
S:spotify=Spotify
S:netflix=Netflix
S:audible=Audible
S:kindle=Kindle
S:humblebundle=Humble Bundle
S:humble bundle=Humble Bundle
S:blinkist=Blinkist
S:likeminded=Likeminded
S:medium.com=Medium
S:quickbooks=QuickBooks
S:oneflow=Oneflow
S:vanta=Vanta
S:hunter.io=Hunter
S:sweep=Sweep
S:telekom=Deutsche Telekom
S:vodafone=Vodafone
S:klarmobil=Klarmobil
S:adference=AdFerence
S:algoexpert=AlgoExpert
S:align=Align
S:amazon prime=Amazon Prime
S:artivive=Artivive
S:ashby=Ashby
S:auditi=Auditi
S:big mountain studio=Big Mountain Studio
S:bluplanet digital=BluPlanet Digital
S:browserless=Browserless
S:capterra=Capterra
S:carriere.it=Carriere.it
S:cello=Cello
S:chatterbug=Chatterbug
S:c.h. beck=C.H. Beck
S:clari=Clari
S:codecademy=Codecademy
S:codenest school=CodeNest School
S:cognism=Cognism
S:contabo=Contabo
S:contentoo=Contentoo
S:contrast=Contrast
S:coresignal=Coresignal
S:coursera=Coursera
S:creative market=Creative Market
S:creditreform=Creditreform
S:cypress=Cypress
S:datacamp=DataCamp
S:datev=DATEV
S:deel=Deel
S:demaai=Dema
S:demostack=Demostack
S:devart=Devart
S:dilisense=Dilisense
S:doit international=DoiT International
S:domain factory=Domain Factory
S:doodle=Doodle
S:dreamdata=Dreamdata
S:dun & bradstreet=Dun & Bradstreet
S:duolingo=Duolingo
S:eaglestatus=EagleStatus
S:eaglestatus.io=EagleStatus.io
S:educative=Educative
S:egghead=Egghead
S:egghead.io=Egghead.io
S:emailable=Emailable
E:exact=Exact
S:financeads=financeAds
S:finanz-szene=Finanz-Szene
S:finapi=finAPI
S:flourish=Flourish
S:fp&a prep=FP&A Prep
S:ftapi=FTAPI
S:geckoboard=Geckoboard
S:genios=GENIOS
S:getcontrast=GetContrast
S:gini=Gini
S:gocardless=GoCardless
S:goodfit=GoodFit
S:grc lab=The GRC Lab
S:groove=Groove
S:growsurf=GrowSurf
S:haufe=Haufe
S:hawk ai=Hawk AI
S:hotjar=Hotjar
S:hoxhunt=HoxHunt
S:humanlinker=Humanlinker
S:icomoon=IcoMoon
S:idnow=IDnow
S:inter.link=Inter.link
S:italki=italki
S:itsg=ITSG
S:jasper=Jasper
S:jumpcloud=JumpCloud
S:kinderheldin=Kinderheldin
S:kinsta=Kinsta
S:klazify=Klazify
S:klippa=Klippa
S:kodekloud=KodeKloud
S:kombo=Kombo
S:kryterion=Kryterion
S:kryterion webassessor=Kryterion Webassessor
S:kudoboard=Kudoboard
S:lacework=Lacework
S:ledgy=Ledgy
S:leetcode=LeetCode
S:lonescale=LoneScale
S:lucanet=LucaNet
S:magix=MAGIX
S:manning=Manning
S:marqeta=Marqeta
S:masterclass=MasterClass
S:mentimeter=Mentimeter
S:michaelpierce.trade=michaelpierce.trade
S:mimestream=Mimestream
S:mirantis=Mirantis
S:modjo=Modjo
S:nerdwallet=NerdWallet
S:netcraft=Netcraft
S:netsuite=NetSuite
S:never5=Never5
S:north data=North Data
S:onfido=Onfido
S:online qr generator=Online QR Generator
S:onthegosystems=OnTheGoSystems
S:open exchange rates=Open Exchange Rates
S:openup=OpenUp
S:openvpn=OpenVPN
S:oracle netsuite=Oracle NetSuite
S:partnerstack=PartnerStack
S:pdfaid=PDFAid
S:pluralsight=Pluralsight
S:portswigger=PortSwigger
S:pragmatic engineer=Pragmatic Engineer
S:preply=Preply
S:pricehubble=PriceHubble
S:prismic=Prismic
S:product growth=Product Growth
S:promlabs=PromLabs
S:proxycurl=Proxycurl
S:proxyman=Proxyman
S:raisin bank=Raisin Bank
S:ravio=Ravio
S:reviewflowz=Reviewflowz
S:rollbar=Rollbar
S:rosetta stone=Rosetta Stone
S:safetyplanner=SafetyPlanner
S:salesloft=Salesloft
S:scoreapp=ScoreApp
S:seibert media=Seibert Media
S:seibert solutions=Seibert Solutions
S:semgrep=Semgrep
S:shecodes=SheCodes
S:skyvia=Skyvia
S:slidespeak=SlideSpeak
S:smallpdf=SmallPDF
S:sofatutor=sofatutor
S:spotler=Spotler
S:squirrly=Squirrly
S:startupdetector=Startupdetector
S:stocksy=Stocksy
S:streem=Streem
S:stripe=Stripe
S:superprof=Superprof
S:surfe=Surfe
S:surveysparrow=SurveySparrow
S:taktile=Taktile
S:techcrunch=TechCrunch
S:terminapp=Terminapp
S:the economist=The Economist
S:thoropass=Thoropass
S:todoist=Todoist
S:total typescript=Total TypeScript
S:transact payments=Transact Payments
S:transkriptor=Transkriptor
S:travelperk=TravelPerk
S:tryhackme=TryHackMe
S:ui.dev=ui.dev
S:unsplash=Unsplash
S:userled=Userled
S:weglot=Weglot
S:wonderway=Wonderway
S:xing=XING
S:yapily=Yapily
S:zavvy=Zavvy
S:monday.com=monday.com
S:freshdesk=Freshdesk
S:sendgrid=SendGrid
S:brevo=Brevo
E:aws=AWS
S:heroku=Heroku
S:paddle=Paddle
S:bitbucket=Bitbucket
S:databricks=Databricks
S:surveymonkey=SurveyMonkey
E:segment=Segment
S:powerbi=Power BI
S:power bi=Power BI
S:okta=Okta
S:1nce=1NCE
S:gong.io=Gong
S:outreach.io=Outreach
S:zoominfo=ZoomInfo
S:close.com=Close
S:retool=Retool
S:wordpress=WordPress
S:moz.com=Moz
S:firebase=Firebase
S:twingate=Twingate
S:nordvpn=NordVPN
S:dashlane=Dashlane
S:crowdstrike=CrowdStrike
S:sophos=Sophos
S:anydesk=AnyDesk
S:gotomeeting=GoToMeeting
S:webex=Webex
S:ringcentral=RingCentral
S:dialpad=Dialpad
S:workday=Workday
S:gusto=Gusto
S:remote.com=Remote
S:greenhouse=Greenhouse
S:lever.co=Lever
S:hellosign=Dropbox Sign
S:confluence=Atlassian
S:basecamp=Basecamp
S:evernote=Evernote
S:obsidian=Obsidian
S:quip=Quip
S:coda.io=Coda
S:smartsheet=Smartsheet
S:wrike=Wrike
S:sana labs=Sana
S:teamlead talks=TeamLead Talks
S:teamleadtalks=TeamLead Talks
S:railsbank=Railsr
S:business insider=Business Insider
S:manager magazin=Manager Magazin
S:related posts=Related Posts for WordPress
S:riecken=Riecken Webservice
S:threejs-journey=Three.js Journey
S:name-cheap=Namecheap
S:qbooks online=QuickBooks Online
S:frontend masters=Frontend Masters
S:linux foundation=Linux Foundation
S:iban.com=IBAN.com
S:cornelsen=Cornelsen eCademy
S:dracula=Dracula Pro
S:corporate finance institute=Corporate Finance Institute
S:apple.com/de=Apple.com/DE
S:amazon business=Amazon Business
S:charliehr=CharlieHR
S:everphone=Everphone
S:urban sports=Urban Sports
S:doktus=Doktus
S:office 365=Microsoft 365
S:cp wave=CP Wave
S:nornorm=Nornorm
S:g2.com=G2.com
S:pult=Pult
S:atlar=Atlar
S:aim-x=AIM-X
S:public cloud group=Public Cloud Group
S:statista=Statista
S:storylane=Storylane
S:medium annual=Medium
S:mindspace=Mindspace
S:topi gmbh=topi
S:ironclad=Ironclad
S:dealfront=Dealfront
S:jobbatical=Jobbatical
S:new work se=New Work SE
S:hyrise=hyrise
S:juicebox=Juicebox
S:peoplegpt=Juicebox
S:magnific=Magnific AI
S:coldreach=Coldreach
S:brandfetch=Brandfetch
S:convert.com=Convert.com
S:babbel=Babbel
S:hipeople=HiPeople
S:frontendmasters=Frontend Masters
S:lennys newsletter=Lenny's Newsletter
S:lyssna=Lyssna
S:usabilityhub=Lyssna
S:maze.design=Maze
S:gaia technologies=GAIA Technologies
E:medium=Medium
E:topi=topi
E:new work=New Work SE
S:newwork,=New Work SE
S:babbel.com=Babbel
S:convertflow=ConvertFlow
S:corporatefinanceinst=CorporateFinanceInst
S:cursor, ai powered=Cursor
E:cursor l&d=Cursor
S:www.dazn.com=DAZN
S:dealfront group=Dealfront
S:everphone finance=Everphone
S:excalidraw=Excalidraw
S:hackinghub=HackingHub
S:iapp.org=IAPP
S:jitter.video=Jitter
E:jitter=Jitter
S:juicebox (peoplegpt)=Juicebox
S:lennysproductpass=Lenny's Newsletter
S:office 365 e3=Microsoft 365
S:orbstack=Orbstack
S:omr reviews=OMR Reviews
S:software reviews gmbh=OMR Reviews
S:lingoda=Lingoda
S:opus clip=Opus Clip
S:veed=VEED
S:superwhisper=Superwhisper
S:benwick=BENWICK
S:callcloud=CallCloud
S:cloudfind=Cloudfind
S:datafabrik=DataFabrik
S:demand conversion=Demand Conversion
S:graphite growth=Graphite Growth
S:levered=Levered
S:powerplay=POWERPLAY
S:pragmaticengineer=Pragmatic Engineer
S:premiumbeat=PremiumBeat
S:sendspark=Sendspark
S:springer.com=Springer
S:www.springer.com=Springer
S:builtformars=Built for Mars
S:fusionbase=Fusionbase
S:matchr.io=Matchr
S:impactradius=Impact
S:impact.com=Impact
S:pplwise=pplwise
S:waybler=Waybler
S:saifedean=Saifedean
S:vistaprint=Vistaprint
S:msft *=Microsoft 365
S:lenny's newsletter=Lenny's Newsletter
S:sonetel=Sonetel
S:atlassin cloud=Seibert Solutions
S:atlassian cloud=Seibert Solutions
S:northdata=North Data
S:climatiq=Climatiq
S:realtimeboard=Miro
S:datazeit=Datazeit
S:gallup=Gallup
E:cockatoo=Cockatoo
S:cockatoo inc=Cockatoo
E:thunderbit=Thunderbit
S:thunderbit, inc=Thunderbit
S:getalign.com=Getalign
E:ionite=Ionite
S:ionite b.v=Ionite
E:akontech=Akontech
E:tradingtwins=tradingtwins
E:monsator=Monsator
S:moreapp=MoreApp
S:theyo labs=Theyo Labs
S:breeze technologies=Breeze Technologies
E:ebitwise=Ebitwise
E:financelabs=FinanceLabs
S:fresh compliance=Fresh Compliance
E:logisticact=LogisticAct
E:passion4business=Passion4Business
S:coaldreach=Coldreach
S:gen25=Gen25
S:dunit international=DoiT International
```

EXCLUDE
```
edeka
rewe
aldi
lidl
jumbo
albert heijn
wolt
lieferando
uber
bolt.eu
freenow
taxi
bahn
lufthansa
ryanair
airbnb
booking.com
hotel
restaurant
cafe
coffee
bäcker
backerei
apotheke
ikea
zv-buchung
umlage
insolvenzgeld
vacation
urlaub
guest:
lunch
dinner
catering
kaution
notar
rechtsanwalt
steuerberater
```
edeka
rewe
aldi
lidl
jumbo
albert heijn
wolt
lieferando
uber
bolt.eu
freenow
taxi
bahn
lufthansa
ryanair
airbnb
booking.com
hotel
restaurant
cafe
coffee
bäcker
backerei
apotheke
ikea
zv-buchung
umlage
insolvenzgeld
vacation
urlaub
guest:
lunch
dinner
catering
kaution
notar
rechtsanwalt
steuerberater
```
edeka
rewe
aldi
lidl
jumbo
albert heijn
wolt
lieferando
uber
bolt.eu
freenow
taxi
bahn
lufthansa
ryanair
airbnb
booking.com
hotel
restaurant
cafe
coffee
bäcker
backerei
apotheke
ikea
zv-buchung
umlage
insolvenzgeld
vacation
urlaub
guest:
lunch
dinner
catering
kaution
notar
rechtsanwalt
steuerberater
```
edeka
rewe
aldi
lidl
jumbo
albert heijn
wolt
lieferando
uber
bolt.eu
freenow
taxi
bahn
lufthansa
ryanair
airbnb
booking.com
hotel
restaurant
cafe
coffee
bäcker
backerei
apotheke
ikea
zv-buchung
umlage
insolvenzgeld
vacation
urlaub
guest:
lunch
dinner
catering
kaution
notar
rechtsanwalt
steuerberater
```
edeka
rewe
aldi
lidl
jumbo
albert heijn
wolt
lieferando
uber
bolt.eu
freenow
taxi
bahn
lufthansa
ryanair
airbnb
booking.com
hotel
restaurant
cafe
coffee
bäcker
backerei
apotheke
ikea
zv-buchung
umlage
insolvenzgeld
vacation
urlaub
guest:
lunch
dinner
catering
kaution
notar
rechtsanwalt
steuerberater
```
edeka
rewe
aldi
lidl
jumbo
albert heijn
wolt
lieferando
uber
bolt.eu
freenow
taxi
bahn
lufthansa
ryanair
airbnb
booking.com
hotel
restaurant
cafe
coffee
bäcker
backerei
apotheke
ikea
zv-buchung
umlage
insolvenzgeld
vacation
urlaub
guest:
lunch
dinner
catering
kaution
notar
rechtsanwalt
steuerberater
```

For each candidate, lowercase it and check:
1. Does it contain any EXCLUDE pattern substring? → drop.
2. Does it match any include pattern (substring or exact)? → add canonical to output, stop checking.
3. No match → add to Pass 2 list.

Do NOT manually re-judge Pass 1 hits. The canonical name the taxonomy gives is the authoritative name.

**3d — Pass 2: your own judgment on unmatched candidates.**

Sort unmatched by tx_count descending. Work through in batches of 300 rows.

Before reviewing: mentally remove obvious noise — names matching travel/food/payroll patterns
(flight, hotel, restaurant, lunch, dinner, rewe, aldi, lohnabrechnung, cross charge, bonus accrual,
premium service for trip, pre billing, writeoff-saasrevenue). Don't include these.

For every remaining unmatched candidate: is this plausibly a real software, SaaS, API, cloud,
fintech, content, learning, or wellbeing digital product? If yes → include. If definitively
not digital → skip. If uncertain → include with ⚠ unverified.

**Canonical naming rule (mandatory).** Use the vendor name exactly as it appears in the
candidate or sample_original — the clearest recognisable form. Do NOT clean it up, translate
it, or simplify it. `APPLE.COM/DE` stays `APPLE.COM/DE`. `G2.com` stays `G2.com`.
`CharlieHR` stays `CharlieHR`. `FRONTENDMASTERS.COM` stays `FRONTENDMASTERS.COM`.
Never write `Apple`, `G2`, `Charlie HR`, or `Frontend Masters` — those are inventions.

**Exhaustion rule (mandatory):** Work through ALL unmatched candidates, not just the top ones.
Do not stop after the first batch. Do not stop because the tx_count looks low.
Real vendors appear at tx_count=2 (e.g. Excalidraw, Orbstack, HACKINGHUB, Jitter).
Only stop when you have reviewed every candidate.

**Anti-fabrication rule (mandatory):** Every vendor you add in Pass 2 MUST correspond to an
actual string that appeared in the merchant column. Never add vendors from general knowledge
of "what companies like this usually buy". If you didn't see the name in the data, it doesn't go in.

**Do not hallucinate (mandatory):** A shorter list with accurate entries is better than a longer list with fabricated ones. If you are not certain a candidate is a real software vendor — mark it ⚠ unverified, do not invent a confident classification. When in doubt, mark ⚠ or leave it out. This applies especially to short strings, abbreviations, and names you don't recognise — do not guess based on what they could plausibly stand for.

**3e — Self-check before presenting.**
Count your output. If you have fewer than 50 vendors from a full-year export of a company
with 50+ employees, something went wrong — either Pass 1 failed to match obvious names, or
Pass 2 stopped too early. Check both before proceeding.

Also check: did you rename any vendor? Scan your output for vendors written as common English
words (`Apple`, `G2`, `Babbel`, `Skool`, `Convert`) that should be the exact candidate string
(`APPLE.COM/DE`, `G2.com`, `BABBEL.COM`, `SKOOL.COM`, `CONVERT.COM`). Fix before presenting.


### Step 4 — Classify, write descriptions, and present the table

This is the step that makes the tool actually useful, do not skip or shortcut it.

Write a one-line description for every vendor that survived Step 3, whether it came from a
Pass 1 match against `$SKILL_DIR/../references/vendor_taxonomy.csv` or from your own Pass 2 judgment. Names
that are clearly not software (a landlord, an insurance company, a law firm, a consultancy, an
individual person's name, a government fee, a bank charge line) stay left out of the table,
quietly, don't ask the user about each one.

**Ambiguity rule (fixed — never coin-flip).** When a Pass 2 candidate is plausibly but not
certainly a software vendor (an unrecognisable name that looks like a product, a company that
sells both software and services, a fragment with too little context), do NOT silently decide
either way: include it in the table marked "⚠ unverified" in the description column, with your
best one-line guess of what it might be. The decision boundary must be stable: recognised
software vendor → include normally; definitively non-software (physical goods, human services,
a person's name) → leave out; everything in between → include with the ⚠ mark. An ambiguous
candidate must never appear in one run and vanish in the next — marked inclusion is the fixed
answer for the grey zone.

Before the table, display the following summary. Fill in the bracketed parts from the actual results — do not change the surrounding text.

> I found approximately **[X] vendors** that appear to be software, SaaS, or AI tools.
>
> **Important:** This is an estimated result. The skill uses a deterministic taxonomy plus an AI pass — it will catch most software spend, but may miss vendors with unusual booking text, and may occasionally include something that is not software. Uncertain vendors are marked ⚠ in the output file.
>
> Vendors I am unsure about: [vendor name(s), or "none"]
>
> [If there are uncertain vendors, add one short explanation here. If there are none, omit this paragraph entirely.]
>
Never flag uncertainty about what a confirmed tool does or how to describe it — writing an accurate description is your job. Don't mention `$SKILL_DIR/../references/vendor_taxonomy.csv` by name, don't mention which pass a vendor came from, and don't mention how many candidates were reviewed or excluded.

Do NOT print the full vendor list in chat. Wait for the user to answer Excel or CSV, then generate the file (Step 5). Only if the user explicitly asks to see the list in chat should you print it there. Vendors from Pass 2 are real findings — present them in the file with the same confidence as Pass 1 matches. ⚠-marked rows sort in the same alphabet, not in a separate section.

### Step 5 — Offer export

**Export purity rule:** the exported file contains ONLY vendor rows — exactly the rows of the
table, nothing else. No summary sentences, no "Note:" rows, no funnel line, no totals row
inside the data. Verify before presenting: every value in the Vendor column must be a vendor
name that also appears in the chat table.

Without waiting for the user to ask — automatically generate an Excel (.xlsx) file and present it using the Artifact/file preview so it opens inline on the right side of the chat.

Write the vendor list (Vendor + Description columns, sorted alphabetically) using openpyxl. Add a note as the last row (Vendor cell empty, Description cell):
"AI-assisted result. May miss vendors with unusual booking text or include uncertain cases (marked ⚠). Verify against source data for financial reporting."

After presenting the file, add one line:
> CSV version also available — just ask.

After presenting the file:

> Share the skill with a colleague who owns software spend, accounting cleanup, procurement review, or the next "wait, what are we paying for?" meeting.
> Send us feedback on what worked, what broke, and what you wanted the skill to catch better.
>
> **This skill is built by the team at Moss** — a spend management platform trusted by 7,000+ companies to automate invoice processing, control card and employee spend, and sync with 40+ accounting and ERP systems in real time. If tracking down software spend manually sounds familiar, Moss is built to fix exactly that.
>
> [getmoss.com](https://www.getmoss.com) · Moss team

---

## Important notes

- `$SKILL_DIR/../references/vendor_taxonomy.csv` is bundled with this skill permanently. It is a static
  snapshot (taken July 2026) of Moss's vendor-tagging patterns, consumed only by
  `scripts/match_taxonomy.py` — do not read it into context or match against it manually.
- Determinism: given the same input file and the same merchant column, steps 3b and 3c must
  produce byte-identical outputs. Only Pass 2 judgments and prose descriptions may vary
  between runs; keep even those stable by applying the fixed inclusion policy and naming
  rules above. It's the live source Moss uses to tag vendor spend in
  production, so it's the primary cross-check for consolidating vendor names and judging what
  counts as software versus noise.
- The file is substantial but not exhaustive. It won't cover every AI startup or niche B2B tool
  a company signs up for, that's what Pass 2 (your own knowledge) is for. A vendor missing from
  the file is not the same as a vendor that isn't software.
- A few of the file's `WHEN` clauses use exact matches instead of `LIKE '%pattern%'` on purpose
  (Moss, Bob, Wix, Vercel, Loom, Bubble, DeepL, and a few others). These are short or common
  enough words that substring matching would produce false positives, keep that same caution in
  mind for Pass 2 names too (e.g. "Canva" vs. "Canvas" the LMS).
- **Mode A only:** `$SKILL_DIR/../references/vendor_taxonomy.csv` is consumed by `scripts/match_taxonomy.py`
  — do not load it into context manually in Mode A. In Mode B it is embedded directly in Step 3
  and must be applied in-context as specified.
- **Mode B only:** the taxonomy is embedded in Step 3 of this skill document. Apply it exactly
  as specified — do not skip Pass 1 or reduce it to a quick mental scan. Pass 1 is the most
  important step and must complete before Pass 2 begins.