require("dotenv").config();
const express = require("express");
const nodemailer = require("nodemailer");

const app = express();

app.use(express.json());

const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: process.env.GMAIL_USER,
    pass: process.env.GMAIL_APP_PASSWORD,
  },
});

app.post("/api/contact", async (req, res) => {
  const { name, email, company, subject, message } = req.body || {};

  if (!name || !email || !subject || !message) {
    return res.status(400).json({ ok: false, error: "Champs obligatoires manquants." });
  }

  try {
    await transporter.sendMail({
      from: `"TAP Site" <${process.env.GMAIL_USER}>`,
      to: process.env.CONTACT_EMAIL || process.env.GMAIL_USER,
      replyTo: email,
      subject: `[Contact TAP] ${subject}`,
      text: `
Nom : ${name}
Email : ${email}
Entreprise : ${company || "-"}

Message :
${message}
      `.trim(),
    });

    res.json({ ok: true });
  } catch (err) {
    console.error("Erreur envoi mail contact :", err);
    res.status(500).json({ ok: false, error: "Erreur lors de l’envoi de l’e-mail." });
  }
});

const PORT = process.env.BACKEND_PORT || 5001;
app.listen(PORT, () => {
  console.log(`Serveur contact TAP démarré sur le port ${PORT}`);
});

