// frontend/src/pages/Rules.jsx
import tilesImg from '../assets/regenwormen-tiles.png'

const h2 = { fontWeight: 900, letterSpacing: '-.015em', fontSize: 24, lineHeight: 1.2, margin: '40px 0 12px', color: '#a8232b' }
const p = { fontSize: 16, lineHeight: 1.7, color: '#4a473f' }

export default function Rules() {
  return (
    <section style={{ maxWidth: 760, margin: '0 auto', padding: '44px 20px 70px' }}>
      <h1 style={{ fontWeight: 900, letterSpacing: '-.015em', fontSize: 'clamp(30px, 5vw, 46px)', lineHeight: 1.06, margin: '0 0 20px', color: '#16150f' }}>Regenwormen spelregels</h1>
      <p style={{ ...p, fontSize: 18 }}>Regenwormen, het spel dat spannend blijft tot de laatste worp! In dit strategische dobbelspel voel je je warempel zo nu en dan zelf bijna een regenworm, kronkelend tussen kansen en risico&rsquo;s, terwijl je probeert zoveel mogelijk tegels met zoveel mogelijk wormen te verzamelen.</p>
      <p style={p}>Met acht dobbelstenen en een flinke stapel tegeltjes biedt Regenwormen een perfecte mix van geluk en tactiek, waarmee zowel kinderen als volwassenen zich urenlang kunnen vermaken. Geen enkele speelronde is hetzelfde, want &eacute;&eacute;n worp te veel kan je van winnaar tot verliezer transformeren!</p>

      <h2 style={h2}>Wat heb je nodig voor een glibberige Regenwormen-sessie?</h2>
      <p style={p}>Voor je wormenfeest heb je natuurlijk het basisspel nodig met z&rsquo;n speciale dobbelstenen en wormentegels. Die 16 tegels zijn genummerd van 21 tot en met 36, en er staan verschillend aantallen regenwormen op. Je kunt het spel spelen met 2 tot 7 spelers, maar het meest ideaal is 3 tot 5 spelers. Op die manier heb je meer kansen om tegels van elkaar te stelen, en dat is nou precies waar de grootste lol zit!</p>
      <p style={{ ...p, fontStyle: 'italic', color: '#54504a', borderLeft: '3px solid #b3ab99', paddingLeft: 16, margin: '22px 0' }}>(Waarom dobbelstenen met regenwormen? Omdat deze kleine glibberige vrienden niet alleen schattig zijn, maar ook de meest waardevolle punten vertegenwoordigen in dit spel. Je zou kunnen zeggen dat de regenworm de aas is in dit kaartspel zonder kaarten!)</p>

      <h2 style={h2}>Voorbereiding: sneller dan een regenworm die in de grond verdwijnt</h2>
      <p style={p}>De voorbereiding is zo eenvoudig dat zelfs een regenworm het zou begrijpen. Leg alle zestien tegels netjes op volgorde in het midden van de tafel, met de laagste waarde (21) helemaal links en de hoogste waarde (36) uiterst rechts. Geef de acht dobbelstenen aan de startspeler, et voil&agrave;! Je bent klaar om te wormen.</p>
      <p style={p}>De startspeler is degene die het meest recent een regenworm in het echt heeft gezien. Geen recente wormenwaarnemingen? Dan begint de jongste speler. Klinkt willekeurig, maar dat is precies de sfeer die we zoeken bij dit spel.</p>
      <figure style={{ margin: '26px 0 0' }}>
        <img src={tilesImg} alt="Regenwormen" style={{ display: 'block', width: '100%', height: 'auto', borderRadius: 2, border: '1px solid #c9c2b1' }} />
        <figcaption style={{ fontSize: 12, fontWeight: 600, color: '#6d6961', marginTop: 8 }}>Regenwormen</figcaption>
      </figure>

      <h2 style={h2}>Tijd om te wormen!</h2>
      <h3 style={{ fontWeight: 900, fontSize: 15, letterSpacing: '.12em', textTransform: 'uppercase', color: '#a8232b', margin: '0 0 12px' }}>De kunst van het dobbelen en selecteren</h3>
      <p style={p}>Als actieve speler werp je alle acht dobbelstenen. Na je worp moet je een beslissing nemen: welke dobbelstenen leg je apart? Je moet kiezen voor alle dobbelstenen met dezelfde waarde OF alle dobbelstenen met een regenworm. Leg deze dobbelstenen apart, want ze vormen jouw score voor deze beurt.</p>
      <p style={p}>Nu komt het zenuwslopende deel: je mag doorgaan met gooien met de overgebleven dobbelstenen. Bij elke volgende worp moet je weer dobbelstenen apart leggen, maar let op &ndash; je moet steeds een ANDERE waarde kiezen dan wat je al apart hebt gelegd. Regenwormen tellen als hun eigen categorie, dus zelfs als je al regenwormen apart hebt gelegd, kun je nog steeds een 1, 2, 3, 4 of 5 kiezen.</p>
      <p style={p}>Na elke worp sta je voor een hartverscheurende beslissing: doorgaan of stoppen? Als je stopt, tel je de waarden van alle apart gelegde dobbelstenen bij elkaar op. Regenwormen tellen stuk voor stuk als 5 punten. Met deze totaalscore kun je een regenwormtegel uit het midden pakken waarvan de waarde overeenkomt met jouw score, OF je kunt een tegel van een tegenstander stelen, als die de exacte waarde heeft die jij net gooide.</p>
      <p style={p}>Maar pas op! Als je na een worp geen nieuwe waarde apart kunt leggen, heb je jezelf klemgezet! Je verliest je beurt &eacute;n de bovenste tegel van jouw stapel, die je beschaamd moet terugleggen naar het midden van de tafel. Zo pijnlijk &hellip;</p>

      <h2 style={h2}>Wanneer de wormen opraken</h2>
      <p style={p}>Het spel gaat door tot alle tegels uit het midden zijn gepakt. Op dat moment telt iedereen het aantal regenwormen op hun verzamelde tegels. De tegels hebben elk een verschillend aantal wormen (van 1 tot 4), dus het is niet alleen de hoeveelheid tegels die telt, maar vooral welke tegels je hebt verzameld. De speler met de meeste regenwormen is de ultieme Wormenkoning(in) en wint het spel!</p>

      <h2 style={h2}>Regenwormtactieken voor Strategische Slimmeriken</h2>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {[
          'Wees niet te gulzig! Vaak is het beter om met een lagere score te stoppen en een tegel te pakken dan door te blijven gooien en alles te verliezen.',
          'Houd je tegenstanders in de gaten! Als je weet dat iemand een tegel met waarde 25 heeft, kun je proberen om precies 25 te gooien en die tegel te stelen.',
          'De regenwormdobbelstenen zijn sleutel tot hoge scores. Elke regenworm telt als 5 punten, dus drie regenwormen alleen al geven je 15 punten!',
          'Begin het spel met lagere tegels. De tegels met lagere waarden hebben soms meer regenwormen, en aan het einde van het spel gaat het om de wormen, niet om de getallen!',
          'Klaar om de aarde om te wroeten en te graven naar glorie? Grijp die dobbelstenen, leg de tegels klaar en ervaar de zinderende spanning van Regenwormen.',
        ].map((text, i) => (
          <li key={i} style={{ ...p, padding: '14px 16px', background: '#f4f0e6', border: '1px solid #ded7c5', borderRadius: 2 }}>{text}</li>
        ))}
      </ul>
    </section>
  )
}
