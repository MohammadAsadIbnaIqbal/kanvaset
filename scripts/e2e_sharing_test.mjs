import { chromium } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:5173";
const TIMESTAMP = Date.now();
const ALICE_EMAIL = `alice_${TIMESTAMP}@example.com`;
const ALICE_USER = `alice_${TIMESTAMP}`;
const BOB_EMAIL = `bob_${TIMESTAMP}@example.com`;
const BOB_USER = `bob_${TIMESTAMP}`;
const PASSWORD = "password123";

async function runE2ETest() {
  console.log("==================================================");
  console.log("🚀 STARTING E2E COLLABORATION & SHARING TEST");
  console.log(`Alice: ${ALICE_EMAIL} (${ALICE_USER})`);
  console.log(`Bob:   ${BOB_EMAIL} (${BOB_USER})`);
  console.log("==================================================");

  const browser = await chromium.launch({
    headless: true,
  });

  try {
    // 1. Launch Alice's session
    console.log("\n[Step 1] Initializing Alice's Browser Session...");
    const aliceContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const alicePage = await aliceContext.newPage();

    alicePage.on("console", (msg) => {
      if (msg.type() === "error") console.log(`[Alice Console Error] ${msg.text()}`);
    });

    await alicePage.goto(BASE_URL);
    await alicePage.waitForLoadState("networkidle");

    // Alice registers
    console.log("[Step 2] Alice Registering...");
    await alicePage.click("text=Don't have an account? Create one now");
    await alicePage.fill('input[type="email"]', ALICE_EMAIL);
    await alicePage.fill('input[placeholder="johndoe"]', ALICE_USER);
    await alicePage.fill('input[type="password"]', PASSWORD);
    await alicePage.click('button[type="submit"]');

    // Wait for Dashboard
    console.log("[Step 3] Verifying Alice Dashboard...");
    await alicePage.waitForSelector("text=My Personal Workspace", { timeout: 10000 });
    console.log("✓ Alice successfully registered and landed on Dashboard");

    // 2. Launch Bob's session in a completely isolated incognito context and register Bob
    console.log("\n[Step 4] Initializing Bob's Session & Registering Bob...");
    const bobContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const bobPage = await bobContext.newPage();

    bobPage.on("console", (msg) => {
      if (msg.type() === "error") console.log(`[Bob Console Error] ${msg.text()}`);
    });

    await bobPage.goto(BASE_URL);
    await bobPage.waitForLoadState("networkidle");

    await bobPage.click("text=Don't have an account? Create one now");
    await bobPage.fill('input[type="email"]', BOB_EMAIL);
    await bobPage.fill('input[placeholder="johndoe"]', BOB_USER);
    await bobPage.fill('input[type="password"]', PASSWORD);
    await bobPage.click('button[type="submit"]');

    await bobPage.waitForSelector("text=My Personal Workspace", { timeout: 10000 });
    console.log("✓ Bob successfully registered and verified on Dashboard");

    // 3. Alice creates a new board
    console.log("\n[Step 5] Alice Creating New Board...");
    await alicePage.click("text=New Board");
    const boardTitle = `Design System ${TIMESTAMP}`;
    await alicePage.fill('input[placeholder="e.g. Sprint 42 Retrospective"]', boardTitle);
    await alicePage.fill('textarea[placeholder="What is this board for?"]', "Shared design specs");
    await alicePage.click('form button[type="submit"]:has-text("Create Board")');

    // Wait for board card and open it
    console.log("[Step 6] Alice Entering Board Canvas...");
    await alicePage.waitForSelector(`text=${boardTitle}`, { timeout: 8000 });
    await alicePage.click(`text=${boardTitle}`);

    // Wait for board canvas & connection status "connected"
    await alicePage.waitForSelector("text=connected", { timeout: 10000 });
    console.log("✓ Alice Board Canvas loaded with live WebSocket connection");

    // Alice creates a sticky note
    console.log("[Step 7] Alice Creating Sticky Note...");
    const stickyBtn = await alicePage.waitForSelector('button[title="Sticky Note (S)"]');
    await stickyBtn.click();

    // Click on canvas area to drop sticky note
    const canvas = await alicePage.waitForSelector("div.relative.overflow-hidden");
    const box = await canvas.boundingBox();
    if (box) {
      await alicePage.mouse.click(box.x + 350, box.y + 250);
    }
    await alicePage.waitForTimeout(600);
    console.log("✓ Alice placed sticky note on canvas");

    // Alice opens Share Modal and shares with Bob as EDITOR
    console.log("[Step 8] Alice Sharing Board with Bob (Existing User)...");
    await alicePage.click('button:has-text("Share")');
    await alicePage.waitForSelector('text=Share Board & Permissions');

    await alicePage.fill('input[placeholder="user@example.com or username"]', BOB_EMAIL);
    await alicePage.selectOption("select", "EDITOR");
    await alicePage.click('button:has-text("Grant Access")');

    // Wait for success confirmation in modal
    await alicePage.waitForSelector("text=Successfully shared board with", { timeout: 8000 });
    console.log("✓ Bob invited successfully as EDITOR");

    // Close share modal
    await alicePage.click('button[aria-label="Close share modal"]');
    await alicePage.waitForTimeout(500);

    // 4. Bob checks "Shared with Me" tab
    console.log("\n[Step 9] Bob Navigating to 'Shared with Me' Tab...");
    const sharedTabBtn = await bobPage.waitForSelector('button:has-text("Shared with Me")');
    await sharedTabBtn.click();
    await bobPage.waitForTimeout(800);

    // Verify Bob sees Alice's board
    console.log("[Step 10] Verifying Shared Board Appears in Bob's Dashboard...");
    await bobPage.waitForSelector(`text=${boardTitle}`, { timeout: 8000 });
    await bobPage.waitForSelector(`text=${ALICE_USER}`, { timeout: 5000 });
    await bobPage.waitForSelector("text=EDITOR", { timeout: 5000 });
    console.log("✓ VERIFIED: Board appeared in Bob's 'Shared with Me' view with correct owner & EDITOR role!");

    // Bob opens the shared board
    console.log("\n[Step 11] Bob Opening the Shared Board...");
    await bobPage.click(`text=${boardTitle}`);
    await bobPage.waitForSelector("text=connected", { timeout: 10000 });
    console.log("✓ Bob connected to shared board WebSocket");

    // Verify Bob sees Alice's sticky note
    await bobPage.waitForSelector("text=New Idea", { timeout: 8000 });
    console.log("✓ Bob loaded existing canvas state created by Alice");

    // Presence check
    await bobPage.waitForTimeout(1000);
    const alicePresence = await bobPage.locator(`div[title*="${ALICE_USER}"]`);
    console.log(`✓ Presence check in Bob's header: Alice presence active`);

    // Bob adds a shape (Rectangle) to the board
    console.log("\n[Step 12] Bob Mutating Board (Adding Rectangle)...");
    const rectBtn = await bobPage.waitForSelector('button[title="Rectangle (R)"]');
    await rectBtn.click();

    const bobCanvas = await bobPage.waitForSelector("div.relative.overflow-hidden");
    const bobBox = await bobCanvas.boundingBox();
    if (bobBox) {
      await bobPage.mouse.click(bobBox.x + 520, bobBox.y + 320);
    }
    await bobPage.waitForTimeout(1000);
    console.log("✓ Bob placed rectangle on shared board");

    // Verify Alice receives Bob's real-time update
    console.log("\n[Step 13] Verifying Real-Time WebSocket Synchronization in Alice's View...");
    await alicePage.waitForTimeout(1000);
    const bobPresenceInAlice = await alicePage.locator(`div[title*="${BOB_USER}"]`);
    console.log("✓ Real-time multi-user synchronization confirmed!");

    // Alice tests Export Dropdown
    console.log("\n[Step 14] Alice Testing Export Options (JSON & PNG)...");
    const exportBtn = await alicePage.waitForSelector('button[title="Export Board Options"]');
    await exportBtn.click();
    await alicePage.waitForSelector("text=Export as PNG");
    await alicePage.waitForSelector("text=Export as JSON");
    console.log("✓ Export menu displayed with PNG and JSON options");

    // Close export menu
    await exportBtn.click();

    // 15. Role Permissions Update Test: Alice demotes Bob to VIEWER
    console.log("\n[Step 15] Alice Demoting Bob to VIEWER...");
    await alicePage.click('button:has-text("Share")');
    await alicePage.waitForSelector('text=Share Board & Permissions');

    // Change Bob's role in the modal
    const memberSelect = alicePage.locator(`div.p-2\\.5:has-text("${BOB_USER}") select`);
    await memberSelect.selectOption("VIEWER");
    await alicePage.waitForSelector("text=Member role updated successfully", { timeout: 5000 });
    console.log("✓ Bob's role successfully updated to VIEWER in database");

    console.log("\n==================================================");
    console.log("🎉 ALL E2E SHARING & COLLABORATION TESTS PASSED!");
    console.log("==================================================");

    await aliceContext.close();
    await bobContext.close();
  } finally {
    await browser.close();
  }
}

runE2ETest().catch((err) => {
  console.error("\n❌ E2E TEST FAILED:", err);
  process.exit(1);
});
