import React from 'react';

export default function Privacy() {
  return (
    <div className="card" style={{ maxWidth: 760, margin: '1.5rem auto' }}>
      <h2>Privacy Policy — TregoCon</h2>
      <p className="muted">Last updated: 2026-08-24</p>

      <h3>What we collect</h3>
      <ul>
        <li><strong>Account:</strong> your display name, email address, and (optionally) a phone number you provide.</li>
        <li><strong>Event participation:</strong> lodging room selections, meal choices, and game sessions you join.</li>
        <li><strong>Photos:</strong> images you upload to the shared photo gallery, plus the attendees and games you tag in them.</li>
      </ul>

      <h3>How we use it</h3>
      <p>
        Solely to coordinate TregoCon and send you <strong>event-related notifications</strong> (for example,
        when registration opens, when your account is approved, and occasional announcements leading up to the event).
        We do <strong>not</strong> use your information for marketing or any purpose unrelated to the event.
      </p>

      <h3>Email &amp; SMS</h3>
      <p>
        Email notifications are sent through Amazon SES. SMS notifications are sent through Twilio.
        These are the only third-party processors involved, and they handle your contact details solely to deliver
        the messages described above.
      </p>

      <h3>Sharing</h3>
      <p>We do <strong>not</strong> sell or share your personal data with any third party beyond the email/SMS processors above.</p>

      <h3>Photos</h3>
      <p>Uploaded photos are visible to registered users of the site. You may delete your own photos at any time.</p>

      <h3>Retention</h3>
      <p>
        We keep your data through the event and beyond — most attendees want their history carried into the following year's
        TregoCon. You can remove your information at any time with the <strong>"Delete my account"</strong> option in
        your account settings, which removes your profile, event selections, and uploaded photos.
      </p>

      <h3>Contact</h3>
      <p>Questions about your data? Email <a href="mailto:trego.comms@tregocon.games">trego.comms@tregocon.games</a>.</p>
    </div>
  );
}
