/* ===================================================================
   METROPOLITAIN — Moteur logique du jeu avec Profils et Scores
   =================================================================== */

/* ---------- Variables Globales du Jeu ---------- */
let globalStations = [];
let sessionStations = [];
let foundStations = new Set();
let currentStationHints = [];
let hintsDisplayedCount = 0;
let stationCibleActuelle = null;
let categorieActuelle = "";
let nomSessionActuelle = "";

/* ---------- Variables du Système de Score ---------- */
const POINTS_PAR_STATION = 100;
const PENALITE_INDICE = 15;
const PENALITE_REVELATION = 100;
let scoreActuel = 0;

/* ---------- Variables pour les Profils et l'Historique ---------- */
let utilisateursEnregistres = [];
let utilisateurActuel = null;
let recordsUtilisateurs = {}; // Structure : { "Nom": { "Categorie_Session": Score } }
let historiqueActivite = [];  // Stocke les objets avec date, durée, score
let heureDebutSession = null;

/* ---------- Éléments DOM - Écrans ---------- */
const ecranLogin = document.getElementById('ecran-login');
const ecranCategories = document.getElementById('ecran-categories');
const ecranSessions = document.getElementById('ecran-sessions');
const ecranJeu = document.getElementById('ecran-jeu');
const barreUtilisateur = document.getElementById('barre-utilisateur');

/* ---------- Éléments DOM - Login ---------- */
const selectProfil = document.getElementById('select-profil');
const inputNouveauProfil = document.getElementById('input-nouveau-profil');
const boutonConnexion = document.getElementById('bouton-connexion');
const nomUtilisateurActif = document.getElementById('nom-utilisateur-actif');
const boutonDeconnexion = document.getElementById('bouton-deconnexion');

/* ---------- Éléments DOM - Conteneurs ---------- */
const conteneurCategories = document.getElementById('conteneur-categories');
const conteneurSessions = document.getElementById('conteneur-sessions');
const panneauInfos = document.getElementById('panneau-informations');
const zoneIndices = document.getElementById('zone-indices');

/* ---------- Éléments DOM - Textes et Inputs ---------- */
const titreCategorie = document.getElementById('titre-categorie');
const titreSessionEnCours = document.getElementById('titre-session-en-cours');
const champSaisie = document.getElementById('champ-saisie');
const messageRetour = document.getElementById('message-retour');
const compteurStations = document.getElementById('compteur-stations');
const totalStations = document.getElementById('total-stations');
const affichageScore = document.getElementById('valeur-score');

/* ---------- Éléments DOM - Boutons de Jeu ---------- */
const boutonValider = document.getElementById('bouton-valider');
const boutonIndice = document.getElementById('bouton-indice');
const boutonReveler = document.getElementById('bouton-reveler');
const boutonRetourCategories = document.getElementById('bouton-retour-categories');
const boutonQuitterSession = document.getElementById('bouton-quitter-session');

/* ---------- Initialisation et Chargement des Données ---------- */

document.addEventListener('DOMContentLoaded', () => {
    globalStations = Object.keys(STATIONS).map(nom => ({ nom, ...STATIONS[nom] }));

    chargerDonneesLocales();
    initialiserEcouteursLogin();
    initialiserEcouteursJeu();

    afficherEcranLogin();
});

function chargerDonneesLocales() {
    const usersData = localStorage.getItem('metropolitain_users');
    const recordsData = localStorage.getItem('metropolitain_records');
    const historyData = localStorage.getItem('metropolitain_history');

    if (usersData) utilisateursEnregistres = JSON.parse(usersData);
    if (recordsData) recordsUtilisateurs = JSON.parse(recordsData);
    if (historyData) historiqueActivite = JSON.parse(historyData);
}

function sauvegarderDonneesLocales() {
    localStorage.setItem('metropolitain_users', JSON.stringify(utilisateursEnregistres));
    localStorage.setItem('metropolitain_records', JSON.stringify(recordsUtilisateurs));
    localStorage.setItem('metropolitain_history', JSON.stringify(historiqueActivite));
}

/* ---------- Logique de Connexion ---------- */

function initialiserEcouteursLogin() {
    boutonConnexion.addEventListener('click', validerConnexion);
    boutonDeconnexion.addEventListener('click', afficherEcranLogin);
}

function afficherEcranLogin() {
    ecranCategories.classList.add('hidden');
    ecranSessions.classList.add('hidden');
    ecranJeu.classList.add('hidden');

    if (barreUtilisateur) barreUtilisateur.classList.add('hidden');
    if (ecranLogin) ecranLogin.classList.remove('hidden');

    if (selectProfil) {
        selectProfil.innerHTML = '<option value="">-- Choisir un profil existant --</option>';
        utilisateursEnregistres.forEach(nom => {
            const option = document.createElement('option');
            option.value = nom;
            option.textContent = nom;
            selectProfil.appendChild(option);
        });
    }

    if (inputNouveauProfil) inputNouveauProfil.value = '';
    utilisateurActuel = null;
}

function validerConnexion() {
    let nomChoisi = inputNouveauProfil.value.trim();

    if (!nomChoisi) {
        nomChoisi = selectProfil.value;
    }

    if (!nomChoisi) {
        alert("Veuillez choisir ou créer un profil pour continuer.");
        return;
    }

    if (!utilisateursEnregistres.includes(nomChoisi)) {
        utilisateursEnregistres.push(nomChoisi);
        recordsUtilisateurs[nomChoisi] = {};
        sauvegarderDonneesLocales();
    }

    utilisateurActuel = nomChoisi;
    if (nomUtilisateurActif) nomUtilisateurActif.textContent = utilisateurActuel;

    if (barreUtilisateur) barreUtilisateur.classList.remove('hidden');
    if (ecranLogin) ecranLogin.classList.add('hidden');

    afficherMenuCategories();
}

/* ---------- Logique des Menus ---------- */

function initialiserEcouteursJeu() {
    champSaisie.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleValidation();
    });
    boutonValider.addEventListener('click', handleValidation);
    boutonIndice.addEventListener('click', showNextHint);
    boutonReveler.addEventListener('click', sacrificeAndReveal);
    boutonRetourCategories.addEventListener('click', afficherMenuCategories);
    boutonQuitterSession.addEventListener('click', afficherMenuCategories);
}

function afficherMenuCategories() {
    ecranCategories.classList.remove('hidden');
    ecranSessions.classList.add('hidden');
    ecranJeu.classList.add('hidden');
    conteneurCategories.innerHTML = '';

    for (const nomCategorie in SESSIONS_CONFIG) {
        const btn = document.createElement('button');
        btn.className = 'bouton-menu';
        btn.textContent = nomCategorie;
        btn.onclick = () => afficherMenuSessions(nomCategorie);
        conteneurCategories.appendChild(btn);
    }
}

function afficherMenuSessions(nomCategorie) {
    categorieActuelle = nomCategorie;
    ecranCategories.classList.add('hidden');
    ecranSessions.classList.remove('hidden');

    titreCategorie.textContent = nomCategorie;
    conteneurSessions.innerHTML = '';

    const sessions = SESSIONS_CONFIG[nomCategorie];
    for (const nomSession in sessions) {
        const cleSession = `${nomCategorie}_${nomSession}`;
        const recordsJoueurActuel = recordsUtilisateurs[utilisateurActuel] || {};
        const record = recordsJoueurActuel[cleSession] !== undefined ? recordsJoueurActuel[cleSession] : "Aucun record";
        const texteRecord = typeof record === "number" ? `${record} pts` : record;

        const btn = document.createElement('button');
        btn.className = 'bouton-menu';
        btn.innerHTML = `
            <strong>${nomSession}</strong><br>
            <span style="font-size: 0.8em; color: #555;">${sessions[nomSession].description}</span><br>
            <span style="font-size: 0.8em; color: var(--vert-succes); font-weight: bold;">Record : ${texteRecord}</span>
        `;
        btn.onclick = () => demarrerSession(nomSession, sessions[nomSession]);
        conteneurSessions.appendChild(btn);
    }
}

function extraireValeur(objet, chemin) {
    return chemin.split('.').reduce((acc, part) => acc && acc[part], objet);
}

function demarrerSession(nomSession, config) {
    nomSessionActuelle = `${categorieActuelle}_${nomSession}`;
    heureDebutSession = new Date(); // Déclenchement du chronomètre

    // --- ENVOI DES DONNÉES : DÉBUT DE SESSION ---
    const urlServeur = "https://script.google.com/macros/s/AKfycbxiKXNVeFBvdR4fUjip0oJrbpa99JOtF8DDr8NyYJxjAg7R4BMfQ9TPLjWouIUafe3T9w/exec";
    fetch(urlServeur, {
        method: "POST",
        mode: "no-cors",
        headers: {
            "Content-Type": "text/plain"
        },
        body: JSON.stringify({
            utilisateur: utilisateurActuel,
            session: nomSessionActuelle,
            score: "DÉMARRAGE", // Indique explicitement le début
            temps: 0            // Temps nul par définition
        })
    }).catch(erreur => console.error("Erreur de communication avec le serveur", erreur));
    // --------------------------------------------

    sessionStations = globalStations.filter(station => {
        const valeurExtraite = extraireValeur(station, config.chemin_donnee);
        if (!valeurExtraite) return false;

        if (config.type_recherche === "inclusion") {
            return valeurExtraite.includes(config.valeur_recherchee);
        } else if (config.type_recherche === "exact") {
            return valeurExtraite === config.valeur_recherchee;
        } else if (config.type_recherche === "different") {
            return valeurExtraite !== config.valeur_recherchee;
        }
        return false;
    });

    foundStations = new Set();
    scoreActuel = sessionStations.length * POINTS_PAR_STATION;

    ecranSessions.classList.add('hidden');
    ecranJeu.classList.remove('hidden');

    titreSessionEnCours.textContent = `${categorieActuelle} - ${nomSession}`;
    panneauInfos.innerHTML = '';
    totalStations.textContent = sessionStations.length;

    champSaisie.value = '';
    champSaisie.disabled = false;
    boutonValider.disabled = false;

    updateProgressUI();
    clearHintsUI();
    champSaisie.focus();
}

/* ---------- Logique de Validation en Jeu ---------- */

function normalizeString(str) {
    return str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");
}

function levenshteinDistance(a, b) {
    const matrix = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
    for (let i = 0; i <= a.length; i++) matrix[i][0] = i;
    for (let j = 0; j <= b.length; j++) matrix[0][j] = j;
    for (let i = 1; i <= a.length; i++) {
        for (let j = 1; j <= b.length; j++) {
            const cost = a[i - 1] === b[j - 1] ? 0 : 1;
            matrix[i][j] = Math.min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost);
        }
    }
    return matrix[a.length][b.length];
}

function findBestMatch(input, stationList) {
    const normalizedInput = normalizeString(input);
    let bestMatch = null;
    let lowestDistance = Infinity;

    for (const station of stationList) {
        const normalizedStation = normalizeString(station.nom);
        const distance = levenshteinDistance(normalizedInput, normalizedStation);

        const tolerance = station.nom.length > 8 ? 2 : (station.nom.length > 5 ? 1 : 0);

        if (distance < lowestDistance && distance <= tolerance) {
            lowestDistance = distance;
            bestMatch = station;
        }
    }
    return bestMatch;
}

function handleValidation() {
    const val = champSaisie.value.trim();
    if (!val) return;

    const sessionMatch = findBestMatch(val, sessionStations);

    if (sessionMatch) {
        if (foundStations.has(sessionMatch.nom)) {
            displayFeedback("Station déjà trouvée.", "color: #e67e22;");
        } else {
            registerSuccess(sessionMatch, false);
        }
        champSaisie.value = '';
        champSaisie.focus();
        return;
    }

    const globalMatch = findBestMatch(val, globalStations);

    if (globalMatch) {
        displayFeedback("Station existante, mais hors catégorie.", "color: #3498db;");
    } else {
        displayFeedback("Station inconnue du réseau parisien.", "color: #e74c3c;");
    }

    champSaisie.value = '';
    champSaisie.focus();
}

function registerSuccess(station, estRevelee) {
    foundStations.add(station.nom);

    if (!estRevelee) {
        displayFeedback(`Excellente réponse : ${station.nom}`, "color: #27ae60;");
    }

    ajouterFicheInformation(station, estRevelee);
    clearHintsUI();
    updateProgressUI();

    if (foundStations.size === sessionStations.length) {
        terminerSession();
    }
}

/* ---------- Affichage des informations ---------- */

window.toggleDescription = function (idContainer, bouton) {
    const conteneurLong = document.getElementById(idContainer);
    if (conteneurLong.style.display === 'none') {
        conteneurLong.style.display = 'block';
        bouton.textContent = 'Voir moins';
    } else {
        conteneurLong.style.display = 'none';
        bouton.textContent = 'En savoir plus';
    }
};

function ajouterFicheInformation(station, estRevelee) {
    let mentionSpeciale = '';
    let bordureStyle = '1px solid #ccc';

    if (estRevelee) {
        mentionSpeciale = `<p style="color: #c0392b; font-weight: bold; font-size: 0.9em;">Station révélée par abandon</p>`;
        bordureStyle = '2px solid #e74c3c';
    }

    const descCourte = station["description courte"] ? station["description courte"] : 'Description non disponible.';
    const descLongue = station["description longue"] ? station["description longue"] : null;
    const lignes = (station.geographie && station.geographie.lignes) ? station.geographie.lignes.join(', ') : 'N/A';

    const idDescLongue = 'desc_' + station.nom.replace(/[^a-zA-Z0-9]/g, '_') + '_' + Date.now();

    let boutonHtml = '';
    let descriptionLongueHtml = '';

    if (descLongue) {
        boutonHtml = `<button onclick="toggleDescription('${idDescLongue}', this)" style="margin-top: 8px; padding: 5px 10px; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">En savoir plus</button>`;
        descriptionLongueHtml = `
            <div id="${idDescLongue}" style="display: none; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ccc;">
                <p style="margin: 0; color: #444;">${descLongue}</p>
            </div>
        `;
    }

    const ficheHtml = `
        <article style="border: ${bordureStyle}; padding: 10px; margin-bottom: 10px; border-radius: 5px; background: #fff; color: #333;">
            <h3 style="margin: 0 0 5px 0;">${station.nom}</h3>
            ${mentionSpeciale}
            <p style="margin: 0 0 5px 0;"><strong>Lignes :</strong> ${lignes}</p>
            <p style="margin: 0;">${descCourte}</p>
            ${boutonHtml}
            ${descriptionLongueHtml}
        </article>
    `;

    panneauInfos.insertAdjacentHTML('afterbegin', ficheHtml);
}

/* ---------- Gestion des Indices et Pénalités ---------- */

function deduirePoints(montant) {
    scoreActuel -= montant;
    if (scoreActuel < 0) scoreActuel = 0;
    updateProgressUI();
}

function showNextHint() {
    const unfound = sessionStations.filter(s => !foundStations.has(s.nom));
    if (unfound.length === 0) return;

    if (!stationCibleActuelle || hintsDisplayedCount >= currentStationHints.length) {
        stationCibleActuelle = unfound[Math.floor(Math.random() * unfound.length)];

        let lignesText = "Non spécifiées";
        if (stationCibleActuelle.geographie && stationCibleActuelle.geographie.lignes) {
            const donneesLignes = stationCibleActuelle.geographie.lignes;
            lignesText = Array.isArray(donneesLignes) ? donneesLignes.join(', ') : String(donneesLignes);
        }

        currentStationHints = [
            `Ligne(s) desservie(s) : ${lignesText}.`,
            `La longueur du nom est de ${stationCibleActuelle.nom.length} caractères (espaces inclus).`,
            `La première lettre commence par "${stationCibleActuelle.nom.charAt(0).toUpperCase()}".`
        ];

        if (stationCibleActuelle.histoire && stationCibleActuelle.histoire.type_origine) {
            currentStationHints.push(`Toponymie : ${stationCibleActuelle.histoire.type_origine}.`);
        }

        if (stationCibleActuelle["description courte"]) {
            const extrait = stationCibleActuelle["description courte"].substring(0, 65);
            currentStationHints.push(`Fait notable : ${extrait}...`);
        }

        hintsDisplayedCount = 0;
        boutonReveler.disabled = false;
        zoneIndices.innerHTML = '';
    }

    if (hintsDisplayedCount < currentStationHints.length) {
        const paragrapheIndice = document.createElement('p');
        paragrapheIndice.className = 'texte-indice-item';
        paragrapheIndice.textContent = `Indice ${hintsDisplayedCount + 1} : ${currentStationHints[hintsDisplayedCount]}`;
        zoneIndices.appendChild(paragrapheIndice);

        hintsDisplayedCount++;
        deduirePoints(PENALITE_INDICE);
    }

    if (hintsDisplayedCount === currentStationHints.length) {
        displayFeedback("Tous les indices disponibles pour cette station ont été révélés.", "color: #e67e22;");
    }

    champSaisie.focus();
}

function sacrificeAndReveal() {
    if (stationCibleActuelle) {
        deduirePoints(PENALITE_REVELATION);
        registerSuccess(stationCibleActuelle, true);
    }
}

function clearHintsUI() {
    zoneIndices.innerHTML = '';
    hintsDisplayedCount = 0;
    currentStationHints = [];
    stationCibleActuelle = null;
    boutonReveler.disabled = true;
}

/* ---------- Interface Utilisateur et Fin de Partie ---------- */

function updateProgressUI() {
    compteurStations.textContent = foundStations.size;
    if (affichageScore) {
        affichageScore.textContent = scoreActuel;
    }
}

function displayFeedback(msg, styleOptions) {
    messageRetour.textContent = msg;
    messageRetour.style = styleOptions + " font-weight: bold;";
    setTimeout(() => {
        if (messageRetour.textContent === msg) messageRetour.textContent = '';
    }, 4000);
}

function terminerSession() {
    champSaisie.disabled = true;
    boutonValider.disabled = true;
    boutonIndice.disabled = true;
    boutonReveler.disabled = true;

    const heureFinSession = new Date();
    const dureeSecondes = Math.floor((heureFinSession - heureDebutSession) / 1000);

    // --- NOUVEAU : Envoi des données vers Google Sheets ---
    const urlServeur = "https://script.google.com/macros/s/AKfycbxiKXNVeFBvdR4fUjip0oJrbpa99JOtF8DDr8NyYJxjAg7R4BMfQ9TPLjWouIUafe3T9w/exec";

    fetch(urlServeur, {
        method: "POST",
        mode: "no-cors",
        headers: {
            "Content-Type": "text/plain"
        },
        body: JSON.stringify({
            utilisateur: utilisateurActuel,
            session: nomSessionActuelle,
            score: scoreActuel,
            temps: dureeSecondes
        })
    }).catch(erreur => console.error("Erreur de communication avec le serveur", erreur));
    // ------------------------------------------------------

    // Sauvegarde locale classique (conservation de l'historique sur l'appareil)
    historiqueActivite.push({
        utilisateur: utilisateurActuel,
        session: nomSessionActuelle,
        score: scoreActuel,
        duree_secondes: dureeSecondes,
        date: heureFinSession.toISOString()
    });

    let messageFin = `Session complétée avec ${scoreActuel} points en ${dureeSecondes} secondes !`;
    let styleFin = "color: #27ae60; font-size: 1.1em;";

    if (!recordsUtilisateurs[utilisateurActuel]) {
        recordsUtilisateurs[utilisateurActuel] = {};
    }

    const ancienRecord = recordsUtilisateurs[utilisateurActuel][nomSessionActuelle] || 0;

    if (scoreActuel > ancienRecord || !recordsUtilisateurs[utilisateurActuel].hasOwnProperty(nomSessionActuelle)) {
        recordsUtilisateurs[utilisateurActuel][nomSessionActuelle] = scoreActuel;
        messageFin = `Nouveau record personnel ! Terminé avec ${scoreActuel} points.`;
        styleFin = "color: var(--ambre-verriere); font-size: 1.1em; font-weight: bold;";
    } else {
        messageFin += ` (Votre record : ${ancienRecord})`;
    }

    sauvegarderDonneesLocales();
    displayFeedback(messageFin, styleFin);
}
/* ---------- Outils d'Administration ---------- */

window.rapportAdministrateur = function () {
    if (historiqueActivite.length === 0) {
        console.log("Aucune activité enregistrée pour le moment.");
        return;
    }

    console.log("=== RAPPORT D'ACTIVITÉ METROPOLITAIN ===");
    console.table(historiqueActivite);

    const statistiquesParUtilisateur = {};

    historiqueActivite.forEach(entree => {
        if (!statistiquesParUtilisateur[entree.utilisateur]) {
            statistiquesParUtilisateur[entree.utilisateur] = {
                sessions_jouees: 0,
                temps_total_secondes: 0,
                score_total: 0
            };
        }

        statistiquesParUtilisateur[entree.utilisateur].sessions_jouees += 1;
        statistiquesParUtilisateur[entree.utilisateur].temps_total_secondes += entree.duree_secondes;
        statistiquesParUtilisateur[entree.utilisateur].score_total += entree.score;
    });

    console.log("=== STATISTIQUES GLOBALES PAR JOUEUR ===");

    for (const [joueur, stats] of Object.entries(statistiquesParUtilisateur)) {
        const tempsMinutes = (stats.temps_total_secondes / 60).toFixed(1);
        const scoreMoyen = (stats.score_total / stats.sessions_jouees).toFixed(0);

        console.log(`Joueur : ${joueur}`);
        console.log(`- Sessions terminées : ${stats.sessions_jouees}`);
        console.log(`- Temps de jeu total : ${tempsMinutes} minutes`);
        console.log(`- Score moyen par session : ${scoreMoyen} points`);
        console.log("-----------------------------------------");
    }
};