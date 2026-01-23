let userId = localStorage.getItem("user_id");

function sendOtp() {
  fetch("/api/send-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.value })
  });
}

function verifyOtp() {
  fetch("/api/verify-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.value, otp: otp.value })
  })
  .then(r => r.json())
  .then(d => {
    localStorage.setItem("user_id", d.user_id);
    userId = d.user_id;
    alert("Logged in");
  });
}

function resolveIssue(id) {
  fetch(`/api/issues/${id}/resolve`, {
    method: "POST",
    headers: { "X-User-Id": userId }
  }).then(loadIssues);
}
