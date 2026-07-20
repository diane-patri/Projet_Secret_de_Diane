/* ===================================================================
   METROPOLITAIN — Moteur logique du jeu avec Système de Score
   =================================================================== */

let globalStations = [];
let sessionStations = [];
let foundStations = new Set();
let currentStationHints = [];
let hintsDisplayedCount = 0;
let stationCibleActuelle = null;
let categorieActuelle = "";
let nomSessionActuelle = "";

// Système de score
const POINTS_PAR_STATION = 100;
const PENALITE_INDICE = 15;
const PENALITE_REVELATION = 100;

let scoreActuel = 0;
let meilleursScores = {};

// Éléments DOM - Écrans
const ecranCategories = document.getElementById('ecran-categories');
const ecranSessions = document.getElementById('ecran-sessions');
const ecranJeu = document.getElementById('ecran-jeu');

// Éléments DOM - Conteneurs
const conteneurCategories = document.getElementById('conteneur-categories');
const conteneurSessions = document.getElementById('conteneur-sessions');
const panneauInfos = document.getElementById('panneau-informations');
const zoneIndices = document.getElementById('zone-indices');

// Éléments DOM - Textes et Inputs
const titreCategorie = document.getElementById('titre-categorie');
const titreSessionEnCours = document.getElementById('titre-session-en-cours');
const champSaisie = document.getElementById('champ-saisie');
const messageRetour = document.getElementById('message-retour');
const compteurStations = document.getElementById('compteur-stations');
const totalStations = document.getElementById('total-stations');
const affichageScore = document.getElementById('valeur-score'); // Nouvel élément

// Éléments DOM - Boutons
const boutonValider = document.getElementById('bouton-valider');
const boutonIndice = document.getElementById('bouton-indice');
const boutonReveler = document.getElementById('bouton-reveler');
const boutonRetourCategories = document.getElementById('bouton-retour-categories');
const boutonQuitterSession = document.getElementById('bouton-quitter-session');

/* ---------- Initialisation ---------- */

document.addEventListener('DOMContentLoaded', () => {
    globalStations = Object.keys(STATIONS).map(nom => ({ nom, ...STATIONS[nom] }));
    
    // Chargement des records sauvegardés dans le navigateur
    const scoresSauvegardes = localStorage.getItem('metropolitain_scores');
    if (scoresSauvegardes) {
        meilleursScores = JSON.parse(scoresSauvegardes);
    }
    
    initialiserEcouteurs();
    afficherMenuCategories();
});

function initialiserEcouteurs() {
    champSaisie.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleValidation();
    });
    boutonValider.addEventListener('click', handleValidation);
    boutonIndice.addEventListener('click', showNextHint);
    boutonReveler.addEventListener('click', sacrificeAndReveal);
    boutonRetourCategories.addEventListener('click', afficherMenuCategories);
    boutonQuitterSession.addEventListener('click', afficherMenuCategories);
}

/* ---------- Navigation Menus ---------- */

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
        // Récupération du record pour l'affichage dans le menu
        const cleSession = `${nomCategorie}_${nomSession}`;
        const record = meilleursScores[cleSession] !== undefined ? meilleursScores[cleSession] : "Aucun record";
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
    
    // Initialisation du score
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

/* ---------- Logique de Validation ---------- */

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

function findBestMatch(input, stationList, maxTolerance = 2) {
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

window.toggleDescription = function(idContainer, bouton) {
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
    if (scoreActuel < 0) scoreActuel = 0; // Sécurité pour empêcher un score négatif
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
        
        // Application de la pénalité pour révélation d'un indice
        deduirePoints(PENALITE_INDICE);
    } 
    
    if (hintsDisplayedCount === currentStationHints.length) {
        displayFeedback("Tous les indices disponibles pour cette station ont été révélés.", "color: #e67e22;");
    }

    champSaisie.focus();
}

function sacrificeAndReveal() {
    if (stationCibleActuelle) {
        // Application de la pénalité pour abandon de la station
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
    
    let messageFin = `Session complétée avec ${scoreActuel} points !`;
    let styleFin = "color: #27ae60; font-size: 1.1em;";

    // Vérification et sauvegarde du meilleur score
    const ancienRecord = meilleursScores[nomSessionActuelle] || 0;
    
    if (scoreActuel > ancienRecord || !meilleursScores.hasOwnProperty(nomSessionActuelle)) {
        meilleursScores[nomSessionActuelle] = scoreActuel;
        localStorage.setItem('metropolitain_scores', JSON.stringify(meilleursScores));
        messageFin = `🔥 Nouveau record ! Vous avez terminé avec ${scoreActuel} points.`;
        styleFin = "color: var(--ambre-verriere); font-size: 1.1em; font-weight: bold;";
    } else {
        messageFin += ` (Record actuel : ${ancienRecord})`;
    }

    displayFeedback(messageFin, styleFin);
}