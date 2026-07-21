# BNZ Customer Intelligence Lab

One demo combining the two ideas:

1. `bank-segmentation-service` supplies behavioural customer segments and eligible synthetic customer IDs.
2. The existing `bnz-ai-marketing-hybrid` service uses Amazon Bedrock to generate a different ad version for each segment.
3. This Lab consumes those finished ad versions; OpenAI-backed synthetic customers test clarity, trust, stress, fairness and accessibility before launch.
4. Amazon Lex V2 receives advisor questions and passes the current campaign/simulation context to an AWS Lambda fulfillment hook.

There is no Supabase dependency and no frontend build step.

## Fastest start on macOS

Double-click `start_all.command`. It starts all three services, opens the Lab in your browser, and keeps them running while its Terminal window stays open.

## Architecture

```text
bank-segmentation-service :8000
  └─ bnz-ai-marketing-hybrid :8010
      ├─ reads ML segments and customer IDs
      └─ Amazon Bedrock generates ad versions
          └─ Customer Intelligence Lab :8020
              ├─ consumes the finished Bedrock versions
              └─ OpenAI synthetic customer assurance
      └─ Amazon Lex V2 Runtime
          └─ Lambda fulfillment
              └─ grounded advisor answer
```

External services have visible fallbacks so the interface remains demoable. The status chips say whether ML, OpenAI and Lex are live or using a fallback.

## 1. Configure the Lab

```bash
cd /Users/huangmaishi/Documents/Codex/2026-07-21/zhe/outputs/bnz-customer-intelligence-lab
cp .env.example .env
```

Open `.env` and add the OpenAI key locally:

```text
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4.1-mini
SEGMENTATION_SERVICE_URL=http://127.0.0.1:8000
MARKETING_SERVICE_URL=http://127.0.0.1:8010
```

Never commit `.env`.

## 2. Start the segmentation service

In terminal 1:

```bash
cd /Users/huangmaishi/Desktop/bank-segmentation-service
source .venv/bin/activate
python -m app.main
```

If it is not running, the Lab uses clearly labelled built-in demo segments.

## 3. Start the existing Bedrock marketing service

In terminal 2:

```bash
cd /Users/huangmaishi/Desktop/bnz-ai-marketing-hybrid
./start_backend.sh
```

It must run on `http://127.0.0.1:8010`. It remains responsible for calling the segmentation service and generating the segment-specific advertisements with Bedrock.

## 4. Start the Customer Lab

In terminal 3:

```bash
cd /Users/huangmaishi/Documents/Codex/2026-07-21/zhe/outputs/bnz-customer-intelligence-lab
chmod +x start.sh
./start.sh
```

Open <http://127.0.0.1:8020>.

## 5. Configure Amazon Lex V2 and Lambda

The local web app can run before this step; the advisor will show a Lex placeholder.

### Deploy the Lambda hook

Install and configure the AWS CLI and AWS SAM CLI, then:

```bash
cd lambda
sam build
sam deploy --guided
```

The deployment output includes `FulfillmentFunctionArn`.

For the hackathon demo, add `OPENAI_API_KEY` to the Lambda function's encrypted environment variables in the AWS console. For production, retrieve it from AWS Secrets Manager instead of storing it directly as an environment variable.

### Create the Lex bot

In Amazon Lex V2:

1. Create a bot such as `BNZCampaignAdvisor` in `ap-southeast-2`.
2. Add the `en_AU` locale.
3. Create an intent named `CampaignAdvisor` with sample utterances such as “Why is this risky?”, “How can I improve the message?”, and “Is this ready to launch?”.
4. Enable the Lambda fulfillment hook for the intent.
5. On the bot alias, attach the deployed Lambda function and grant Lex permission to invoke it.
6. Build the locale and create or update the bot alias.

Copy these values into the Lab `.env`:

```text
AWS_REGION=ap-southeast-2
AWS_PROFILE=your-local-profile
LEX_BOT_ID=your-bot-id
LEX_BOT_ALIAS_ID=your-alias-id
LEX_LOCALE_ID=en_AU
```

Restart `./start.sh`. The header should now show `Lex configured`. Every chat request carries a compact `simulationContext` session attribute; Lex passes it to Lambda so the answer stays grounded in the selected campaign and customer-risk evidence.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Safety boundaries

- Segmentation uses behavioural signals, not inferred protected identity.
- Generated messages must not imply approval or invent rates, fees or eligibility.
- Synthetic customer results are an early risk screen, not a substitute for compliance, accessibility or real customer research.
- Sample customer IDs and all bundled audiences are synthetic.
