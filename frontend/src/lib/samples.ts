import type { Channel } from "../types";

/** One-click sample messages so the app can be tried without real client data. */
export const SAMPLES: Record<Channel, { sender: string; content: string }> = {
  whatsapp: {
    sender: "Sara (client)",
    content:
      "Small change for the website: please remove card payments and add JazzCash and Bank Transfer instead. Also make the homepage look more premium. We still need to launch on 30 Nov.",
  },
  email: {
    sender: "sara@acme-traders.example",
    content:
      "Subject: Change request: payment methods and homepage banner\n\nHi Ali,\n\nFollowing my WhatsApp message, here are the changes in writing. Please add JazzCash and Bank Transfer as payment options. The homepage must show one banner with a single Shop now button instead of the slider. The site should load within 3 seconds.\n\nThanks,\nSara",
  },
  meeting_transcript: {
    sender: "",
    content:
      "[10:02] Sara: We want customers to track their order status from their account page.\n[10:04] Sara: The site must load within 5 seconds on mobile.\n[10:05] Ali: Noted, we will check the load time against the earlier email.",
  },
  document: {
    sender: "",
    content:
      "Order tracking\n\nCustomers need an order tracking page showing the delivery status.\n\nAdmin panel\n\nStaff should be able to export orders as a spreadsheet.",
  },
};
