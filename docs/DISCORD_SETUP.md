# Discord Notification Setup Guide

This guide covers how to configure Discord notifications for the auto-maintain workflow.

## 1. Add the Secret to the Repository

The `DISCORD_WEBHOOK_URL` secret must be added to the `answering-automation-infra` repository:

1. Navigate to: **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `DISCORD_WEBHOOK_URL`
3. Value: `https://discord.com/api/webhooks/1512875186259628294/DSxEfw4gKiczsdNcZWg-aISM6BKJWaJnup7BT1qIcRG9hxuni2sq7kXyHhygt6A7fuln`

## 2. Workflow Configuration

The reusable workflow `.github/workflows/auto-maintain-reusable.yml` declares the secret as **optional** (`required: false`):

```yaml
secrets:
  DISCORD_WEBHOOK_URL:
    required: false
```

This ensures **backward compatibility** (NFR3) - existing consumer repos that don't pass this secret will continue to work. Notifications will simply be skipped silently.

## 3. Validation Checklist

### 3.1 Secret Access Test

- [ ] `DISCORD_WEBHOOK_URL` is configured in repository secrets
- [ ] Secret is accessible in workflow runs (check workflow logs for "DISCORD_WEBHOOK_URL not configured" messages)

### 3.2 Notification Flow Test

Trigger a manual workflow run and verify all three Discord notifications fire:

- [ ] **Started notification**: "🚀 Auto Maintain Started" (blue, color: 3447003)
  - Fields: Repo, Item, Run link
- [ ] **Completed notification**: "✅ Auto Maintain Completed" (green, color: 5763719)
  - Fields: Repo, Duration, Cost, PR link
  - Only fires on `success()`
- [ ] **Failed notification**: "❌ Auto Maintain Failed" (red, color: 15158332)
  - Fields: Repo, Duration, Reason, Run link
  - Only fires on `failure()`

### 3.3 COSTS.md Compatibility Test

Verify that both modes produce valid `COSTS.md` entries:

- [ ] **GitHub Issues mode**: Item ID and title populate correctly
- [ ] **BACKLOG.md mode** (legacy): Item ID and title populate correctly

### 3.4 Backward Compatibility Test

Simulate a consumer without the secret:

- [ ] Remove or comment out `DISCORD_WEBHOOK_URL` from secrets temporarily
- [ ] Run workflow
- [ ] Workflow completes successfully (no errors)
- [ ] Notification steps show "DISCORD_WEBHOOK_URL not configured, skipping notification"
- [ ] `continue-on-error: true` prevents failures

### 3.5 Consumer Workflow Test

Verify no existing consumer `AutoMaintain.yml` files require modification:

- [ ] Consumer workflows continue to work without passing `DISCORD_WEBHOOK_URL`
- [ ] Optional secret design maintains compatibility

## 4. Expected Behavior

| Scenario | Expected Result |
|----------|----------------|
| Secret configured | All 3 notifications fire (started, completed/failed, optional long-running) |
| Secret not configured | Workflow completes silently, no notifications sent |
| Notification fails (network error) | Workflow continues (`continue-on-error: true`) |
| Consumer doesn't pass secret | Workflow works normally, no breaking changes |

## 5. Troubleshooting

### No notifications received

1. Check secret is configured: Settings → Secrets and variables → Actions
2. Check workflow logs for "DISCORD_WEBHOOK_URL not configured"
3. Verify webhook URL is valid (test with curl)
4. Check Discord channel permissions

### Notifications fail but workflow succeeds

This is expected! All notification steps use `continue-on-error: true` to prevent blocking the workflow on notification failures.

### Consumer workflows break

This should not happen since `required: false`. If it does:
1. Verify consumer is calling the updated workflow version
2. Check consumer doesn't have validation expecting the secret

## 6. Integration Points

The notification system integrates with:

- **Duration tracking** (`calculate-duration` step)
- **Token usage extraction** (`token-usage` step)
- **COSTS.md logging** (appended after Claude session)
- **PR creation** (`verify-pr` step)

All dependencies are already implemented in the workflow.

## 7. Security Notes

- Webhook URL is stored as a **repository secret**, not hardcoded
- Secrets are never logged or exposed in workflow output
- Failed notification attempts do not expose the webhook URL
- Consumer repos don't need access to the secret (centralized in infra repo)
