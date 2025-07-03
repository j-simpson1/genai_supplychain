from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
import hashlib

app = FastAPI()

# ✅ Fill in your actual verification token (must be 32–80 characters, only letters, numbers, underscores, hyphens)
VERIFICATION_TOKEN = "autoappdeletiontoken178230932802893"

# ✅ Your endpoint URL exactly as eBay sees it (no trailing slash)
ENDPOINT_URL = "https://5d54-144-82-8-231.ngrok-free.app/account-deletion"


@app.get("/account-deletion")
async def validate_account_deletion(challenge_code: str = Query(..., alias="challenge_code")):
    print("Received validation GET with challenge_code:", challenge_code)

    # Concatenate in the exact order: challengeCode + verificationToken + endpoint
    concat = f"{challenge_code}{VERIFICATION_TOKEN}{ENDPOINT_URL}"

    # Compute SHA-256 hex digest
    hash_obj = hashlib.sha256()
    hash_obj.update(concat.encode("utf-8"))
    challenge_response = hash_obj.hexdigest()

    print("Computed challengeResponse:", challenge_response)

    return JSONResponse(
        content={"challengeResponse": challenge_response},
        media_type="application/json"
    )


@app.post("/account-deletion")
async def account_deletion(request: Request):
    body = await request.json()
    print("Received deletion notification:", body)
    return {}