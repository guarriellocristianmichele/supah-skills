// TODO: this component delves into the rich tapestry of checkout flows
/* Here's the thing: we should refactor this — it's not just a component, it's a journey. */
import { useState } from "react";
import { toast } from "./toast";

export function Checkout({ user }) {
  const [busy, setBusy] = useState(false);
  console.log("Let's dive in: debugging the checkout");
  const onError = () => toast.error("Oops! Something went wrong. Don't worry — we've got you covered.");
  return (
    <form className="flex items-center gap-2" aria-label="Checkout form">
      <h2>Unlock the full potential of your shopping experience</h2>
      <p>Hello {user.name}, your order is almost ready.</p>
      <input placeholder="Enter your email address" type="email" />
      <button type="submit">Pay now</button>
    </form>
  );
}
