# BNZ Customer Intelligence Lab

An AI-assisted pre-launch assurance layer for personalised banking campaigns, developed for the University of Auckland × BNZ Hackathon.

The Customer Intelligence Lab extends the BNZ AI Marketing Acceleration Platform by testing how different synthetic customers may interpret, trust, or react to each segment-specific advertisement before a campaign is released. It combines behavioural customer segmentation, Amazon Bedrock campaign generation, OpenAI-backed synthetic customer simulation, and an Amazon Lex V2 advisor with AWS Lambda fulfillment.

> This project is an early risk-screening demo. It does not replace customer research, accessibility testing, legal review, compliance approval, or operational readiness checks.

## Platform repositories

The end-to-end platform is intentionally separated into three services with clear responsibilities:

| Repository | Responsibility | Local port |
|---|---|---:|
| [`bank-segmentation-service`](https://github.com/Maishi226/bank-segmentation-service) | Produces behavioural customer segments and eligible synthetic customer IDs using K-Means clustering. | `8000` |
| [`bnz-ai-marketing-hybrid`](https://github.com/Maishi226/bnz-ai-marketing-hybrid) | Retrieves ML audiences and uses Amazon Bedrock to generate a different advertisement for each segment. | `8010` |
| [`bnz-customer-intelligence-lab`](https://github.com/Maishi226/bnz-customer-intelligence-lab) | Evaluates the finished Bedrock advertisements using synthetic customer reactions and provides a Lex/Lambda campaign advisor. | `8020` |

## End-to-end workflow

1. A bank employee enters a product or campaign brief.
2. `bnz-ai-marketing-hybrid` calls `bank-segmentation-service` for behavioural segments and eligible synthetic customer IDs.
3. Amazon Bedrock generates a distinct advertising version for every selected segment.
4. The Lab consumes those finished versions without replacing the Bedrock copy.
5. Synthetic customers evaluate clarity, trust, stress, fairness, accessibility, and overall launch readiness.
6. The Lab presents segment-level risks, recommendations, and a safer rewrite for review.
7. Campaign context is passed to Amazon Lex V2 as a session attribute; Lex invokes AWS Lambda to return a grounded advisor response.

## Architecture

```text
                         Bank employee
                               │
                               ▼
              BNZ AI Marketing Hybrid (:8010)
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
   Segmentation Service (:8000)       Amazon Bedrock
   • behavioural clusters             • segment-specific ads
   • synthetic customer IDs           • grounded campaign copy
                │                             │
                └──────────────┬──────────────┘
                               ▼
              Customer Intelligence Lab (:8020)
              • synthetic customer reactions
              • risk and readiness scorecards
              • recommendations and safer copy
                               │
                               ▼
                     Amazon Lex V2 advisor
                               │
                               ▼
                    AWS Lambda fulfillment
```

## Key capabilities

- **Behavioural targeting evidence** — displays the ML segment, audience size, confidence, and sample synthetic customer IDs used by the upstream marketing service.
- **Bedrock creative traceability** — preserves the headline, message, CTA, and generation status returned by `bnz-ai-marketing-hybrid`.
- **Synthetic customer assurance** — evaluates likely reactions across customer contexts rather than relying on a single aggregate score.
- **Multi-dimensional risk signals** — measures clarity, trust, stress, fairness, accessibility, and launch readiness.
- **Grounded campaign advisor** — passes the selected campaign and simulation evidence through Amazon Lex V2 to a Lambda fulfillment hook.
- **Resilient demonstration mode** — clearly labelled fallbacks keep the interface demonstrable when an external service is unavailable.

## Prerequisites

- macOS or Linux
- Python 3.11 or later
- AWS CLI configured with IAM Identity Center (SSO) or another supported credential provider
- AWS SAM CLI for deploying the Lambda fulfillment hook
- Access to Amazon Bedrock and Amazon Lex V2 in the configured AWS Region
- An OpenAI API key for synthetic customer evaluation

## Installation

Clone all three repositories into the same parent directory:

```bash
git clone https://github.com/Maishi226/bank-segmentation-service.git
git clone https://github.com/Maishi226/bnz-ai-marketing-hybrid.git
git clone https://github.com/Maishi226/bnz-customer-intelligence-lab.git
```

The recommended layout is:

```text
bnz-platform/
├── bank-segmentation-service/
├── bnz-ai-marketing-hybrid/
└── bnz-customer-intelligence-lab/
```

### Install the segmentation service

```bash
cd bank-segmentation-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/train_model.py
deactivate
cd ..
```

### Install the marketing service

```bash
cd bnz-ai-marketing-hybrid
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
deactivate
cd ..
```

### Install the Customer Intelligence Lab

```bash
cd bnz-customer-intelligence-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Edit the Lab `.env` file:

```dotenv
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4.1-mini

SEGMENTATION_SERVICE_URL=http://127.0.0.1:8000
MARKETING_SERVICE_URL=http://127.0.0.1:8010

AWS_PROFILE=your-aws-profile
AWS_REGION=ap-southeast-2
LEX_BOT_ID=your-lex-bot-id
LEX_BOT_ALIAS_ID=your-lex-alias-id
LEX_LOCALE_ID=en_AU
```

Never commit `.env`, AWS credentials, or API keys. The repository includes only `.env.example`.

If the repositories are not sibling folders, add their locations to `.env`:

```dotenv
SEGMENT_REPO_DIR=/path/to/bank-segmentation-service
MARKETING_REPO_DIR=/path/to/bnz-ai-marketing-hybrid
```

## Run the complete platform

Authenticate with AWS:

```bash
aws sso login --profile your-aws-profile
```

From `bnz-customer-intelligence-lab`, run:

```bash
chmod +x start_all.command
./start_all.command
```

The launcher:

- validates required configuration;
- checks the AWS session;
- starts all three services;
- verifies ports `8000`, `8010`, and `8020`;
- confirms OpenAI and Lex configuration was loaded;
- opens <http://127.0.0.1:8020>.

Keep the terminal window open while using the platform. Press `Control-C` to stop the services.

### Run services individually

```bash
# Terminal 1
cd bank-segmentation-service
source .venv/bin/activate
python -m app.main

# Terminal 2
cd bnz-ai-marketing-hybrid
source .venv/bin/activate
uvicorn backend.app:app --host 127.0.0.1 --port 8010

# Terminal 3
cd bnz-customer-intelligence-lab
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8020
```

## Service integration

The Lab uses the upstream services rather than reimplementing their responsibilities:

```text
GET  bank-segmentation-service/v1/segments
GET  bank-segmentation-service/v1/customers?segment_id={id}

POST bnz-ai-marketing-hybrid/api/generate
     └─ returns campaign[].creative generated by Amazon Bedrock

POST bnz-customer-intelligence-lab/api/campaigns
     └─ evaluates each upstream creative with synthetic customers

POST bnz-customer-intelligence-lab/api/chat
     └─ calls Amazon Lex V2 with simulationContext
```

The Lab copies each upstream `headline`, `message`, and `cta` into its evaluation request. It does not silently replace Bedrock-generated creative.

## Amazon Lex V2 and Lambda

The Lambda fulfillment implementation and AWS SAM template are provided in [`lambda/`](lambda/).

Deploy the function:

```bash
cd lambda
sam build
sam deploy --guided
```

In Amazon Lex V2:

1. Create or select a bot in the same AWS Region.
2. Add the `en_AU` locale and a `CampaignAdvisor` intent.
3. Add representative utterances such as “Why is this risky?”, “How can I improve this message?”, and “Is this ready to launch?”.
4. Enable fulfillment for the intent.
5. Attach the deployed Lambda function to the bot alias and grant Lex permission to invoke it.
6. Build the locale and publish the alias.
7. Add the Bot ID and Alias ID to the Lab `.env`.

The Lab serialises the active campaign and its simulation result into the `simulationContext` Lex session attribute. Lambda uses that evidence to answer questions without inventing campaign terms.

## Testing

```bash
source .venv/bin/activate
pytest -q
```

The automated tests cover service health, fallback audiences, campaign evaluation, and Lambda fulfillment response structure.

## Privacy, safety, and limitations

- All bundled customer records and identifiers are synthetic.
- Segmentation is based on behavioural signals rather than names, passports, addresses, occupations, or inferred protected characteristics.
- The platform does not send advertisements or make credit decisions.
- Generated content must not imply guaranteed approval or invent rates, fees, eligibility, or legal terms.
- Synthetic customer scores are directional risk signals, not calibrated predictions of real customer behaviour.
- High-impact campaigns still require accessibility testing, compliance review, operational review, and research with real customers.

## Technology stack

- Python and FastAPI
- JavaScript, HTML, and CSS
- scikit-learn K-Means clustering
- Amazon Bedrock
- Amazon Lex V2
- AWS Lambda and AWS SAM
- OpenAI Responses API
- AWS IAM Identity Center (SSO)

## Future development

- Deploy the three services using AWS Lambda, ECS, or another managed runtime.
- Store OpenAI credentials in AWS Secrets Manager for deployed environments.
- Add campaign version comparison and human approval workflows.
- Introduce feedback loops from campaign performance and real customer research.
- Add automated accessibility and policy regression tests.
