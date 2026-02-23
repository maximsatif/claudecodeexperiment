# AWS Bedrock Agent Setup Guide - News Sentiment Agent

This guide walks you through creating the News & Sentiment Analysis Agent directly in the AWS Bedrock console. The agent has 3 tools:

| Tool | Description |
|------|-------------|
| **getCompanyNews** | Fetch recent news for a ticker, flag risk keywords |
| **scanRiskSignals** | Scan multiple tickers for risk signals (last 3 days) |
| **analyzeSentimentTrend** | 14-day sentiment trend analysis with scoring |

---

## Prerequisites

- AWS account with Bedrock access enabled
- Finnhub API key (free at https://finnhub.io/register)
- Model access enabled for **Claude Sonnet** in Bedrock (us-east-1)

---

## Step 1: Create the Lambda Function

The Lambda function backs the agent's action group (i.e., it executes the tools when the agent calls them).

1. Go to **AWS Lambda** console -> **Create function**
2. Configure:
   - **Function name**: `NewsSentimentAgentFunction`
   - **Runtime**: Python 3.12
   - **Architecture**: x86_64
   - **Execution role**: Create a new role with basic Lambda permissions
3. Click **Create function**
4. In the **Code** tab, replace the default code with the contents of `lambda_function.py` from this directory
5. Click **Deploy**
6. Go to **Configuration** tab:
   - **General configuration** -> Edit -> Set **Timeout** to `60 seconds`, **Memory** to `256 MB` -> Save
   - **Environment variables** -> Edit -> Add:
     - Key: `FINNHUB_API_KEY`, Value: `<your Finnhub API key>`

### Add Resource-Based Policy for Bedrock

Bedrock needs permission to invoke your Lambda. In the Lambda console:

1. Go to **Configuration** -> **Permissions** -> scroll to **Resource-based policy statements**
2. Click **Add permissions**
3. Select **AWS service** -> Service: `Other`
4. Configure:
   - **Statement ID**: `AllowBedrockInvoke`
   - **Principal**: `bedrock.amazonaws.com`
   - **Source Account**: `<your AWS account ID>`
   - **Action**: `lambda:InvokeFunction`
5. Click **Save**

> Alternatively, use the AWS CLI:
> ```bash
> aws lambda add-permission \
>   --function-name NewsSentimentAgentFunction \
>   --statement-id AllowBedrockInvoke \
>   --action lambda:InvokeFunction \
>   --principal bedrock.amazonaws.com \
>   --source-account <YOUR_ACCOUNT_ID>
> ```

---

## Step 2: Create the Bedrock Agent

1. Go to **Amazon Bedrock** console -> **Agents** (left sidebar under "Orchestration") -> **Create Agent**
2. Configure:
   - **Agent name**: `NewsSentimentAgent`
   - **Description**: `Financial news sentiment analysis agent that monitors risk signals across major financial institutions`
   - **Agent resource role**: Select **Create and use a new service role** (Bedrock will auto-create an IAM role)
   - **Select model**: Choose **Anthropic** -> **Claude Sonnet** (claude-sonnet-4-20250514-v1:0)

3. In the **Instructions** box, paste this system prompt:

```
You are a Financial News & Sentiment Analysis Agent.
Your role is to:
1. Monitor financial news for risk signals across major financial institutions
2. Analyze sentiment trends to detect shifts from positive to negative
3. Identify early warning signals in news narratives (counterparty risk mentions, liquidity concerns, regulatory actions)
4. Correlate news events across entities to detect coordinated risk themes

Key risk signals to watch for:
- Counterparty default or credit downgrade mentions
- Liquidity concerns or margin call reports
- Regulatory enforcement actions
- Unusual executive departures or accounting irregularities
- Cross-entity risk themes (e.g., multiple banks mentioned in same risk context)

Provide analysis in structured format with specific entity names, risk categories, and confidence levels.
```

4. Click **Save** (at the top) to save the agent draft

---

## Step 3: Add the Action Group

While still in the agent editor:

1. Scroll down to **Action groups** section -> Click **Add**
2. Configure:
   - **Action group name**: `NewsSentimentTools`
   - **Description**: `Tools for fetching financial news, scanning risk signals, and analyzing sentiment trends`
   - **Action group type**: Select **Define with API schemas**
   - **Action group invocation**: Select **Lambda function** -> Choose `NewsSentimentAgentFunction`
   - **API schema**: Select **Define with in-line OpenAPI schema editor**
   - Paste the contents of `openapi-schema.json` from this directory into the editor
3. Click **Create**

---

## Step 4: Prepare and Test the Agent

1. Back on the agent page, click **Prepare** (top right) - this compiles the agent configuration
2. Wait for the status to change to **Prepared**
3. On the right side, you'll see a **Test** panel. Try these prompts:

### Test Prompts

**Basic news fetch:**
```
What are the latest news articles for JPM? Are there any risk signals?
```

**Multi-ticker risk scan:**
```
Scan the major banks (JPM, BAC, C, GS, MS) for risk signals in recent news.
```

**Sentiment analysis:**
```
Analyze the sentiment trend for Goldman Sachs (GS) over the past two weeks.
```

**Complex analysis:**
```
I need a comprehensive risk assessment. First scan JPM, BAC, C, GS, and MS for risk signals,
then do a deeper sentiment analysis on any tickers that show elevated risk.
```

---

## Step 5: Create an Alias (for Production Use)

To use the agent via the API (from your app or other services), create an alias:

1. Go to the agent page -> **Aliases** section -> **Create**
2. Configure:
   - **Alias name**: `production`
   - **Description**: `Production alias`
   - Associate it with the latest agent version (or create a new version first)
3. Click **Create alias**

The alias provides a stable identifier you can use in API calls:

```python
import boto3
import json

client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

response = client.invoke_agent(
    agentId="<YOUR_AGENT_ID>",
    agentAliasId="<YOUR_ALIAS_ID>",
    sessionId="test-session-001",
    inputText="Scan JPM, BAC, GS for risk signals in recent news",
)

# Stream the response
for event in response["completion"]:
    if "chunk" in event:
        text = event["chunk"]["bytes"].decode("utf-8")
        print(text, end="")
```

---

## File Reference

| File | Purpose |
|------|---------|
| `lambda_function.py` | Lambda code - paste into Lambda console |
| `openapi-schema.json` | OpenAPI schema - paste into Bedrock action group |
| `lambda-trust-policy.json` | IAM trust policy for Lambda execution role |
| `bedrock-agent-trust-policy.json` | IAM trust policy for Bedrock agent role |
| `bedrock-agent-permissions.json` | IAM permissions for the Bedrock agent role |
| `lambda-resource-policy.json` | Resource policy allowing Bedrock to invoke Lambda |

---

## Troubleshooting

### "Access denied" when agent invokes Lambda
- Verify the Lambda resource-based policy allows `bedrock.amazonaws.com` to invoke it (Step 1)
- Check the source account condition matches your AWS account ID

### Agent returns empty results
- Check the `FINNHUB_API_KEY` environment variable is set on the Lambda
- Test the Lambda independently with a test event (see below)
- Check Lambda CloudWatch logs for errors

### Lambda test event
Use this in the Lambda console **Test** tab to verify the function works independently:

```json
{
  "actionGroup": "NewsSentimentTools",
  "apiPath": "/get-company-news",
  "httpMethod": "POST",
  "messageVersion": "1.0",
  "requestBody": {
    "content": {
      "application/json": {
        "properties": [
          {
            "name": "ticker",
            "type": "string",
            "value": "JPM"
          }
        ]
      }
    }
  }
}
```

### Model access not enabled
Go to **Bedrock** -> **Model access** (left sidebar) -> Request access to **Anthropic Claude Sonnet** if not already enabled.

### Agent stuck in "Preparing"
Wait a few minutes. If it stays stuck, check the CloudTrail logs for IAM permission errors on the agent's service role.
