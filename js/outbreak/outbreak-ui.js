/* outbreak-ui.js — controles e painel do modo Outbreak.
 * Depende de window.Outbreak (outbreak.js) e de uma API Python em /api/outbreak.
 */
(() => {
    "use strict";

    const controls = document.getElementById("controls");
    if (!controls || !window.Outbreak) return;

    const panel = document.createElement("section");
    panel.id = "outbreak-panel";
    panel.innerHTML = `
        <h3>Outbreak Simulator</h3>
        <p class="outbreak-description">Dia sintético de tempo severo — não representa condições meteorológicas reais.</p>
        <label for="outbreak-risk">Nível de risco</label>
        <select id="outbreak-risk">
            <option value="Marginal">Marginal</option>
            <option value="Slight" selected>Slight</option>
            <option value="Enhanced">Enhanced</option>
            <option value="Moderate">Moderate</option>
            <option value="High">High</option>
        </select>
        <label for="outbreak-seed">Seed</label>
        <input id="outbreak-seed" type="number" value="7" step="1">
        <div class="outbreak-actions">
            <button id="outbreak-start" type="button">Iniciar dia</button>
            <button id="outbreak-pause" type="button">Pausar</button>
            <button id="outbreak-resume" type="button">Continuar</button>
            <button id="outbreak-reset" type="button">Reiniciar</button>
        </div>
        <p id="outbreak-status" role="status" aria-live="polite">Backend Python ainda não conectado.</p>
        <div id="outbreak-summary"></div>
    `;

    const alerts = document.getElementById("alerts-box");
    controls.insertBefore(panel, alerts || null);

    const $ = id => document.getElementById(id);
    const status = $("outbreak-status");
    const summary = $("outbreak-summary");
    const buttons = ["outbreak-start", "outbreak-pause", "outbreak-resume", "outbreak-reset"];

    function setStatus(message, error = false) {
        status.textContent = message;
        status.classList.toggle("outbreak-error", error);
    }

    function showSummary(data) {
        if (!data || typeof data !== "object") return;
        const score = data.score || data.summary || data;
        const fields = [
            ["Tornados", score.tornados],
            ["Alertas", score.alertas],
            ["Avisados antes", score.avisados_antes],
            ["Antecedência média", score["antecedência_média_min"] == null ? null : score["antecedência_média_min"] + " min"],
            ["Sem aviso", score.sem_aviso],
            ["Alarmes falsos", score.alarmes_falsos]
        ].filter(([, value]) => value !== undefined && value !== null);

        summary.replaceChildren();
        if (!fields.length) return;
        const list = document.createElement("dl");
        for (const [label, value] of fields) {
            const dt = document.createElement("dt");
            const dd = document.createElement("dd");
            dt.textContent = label;
            dd.textContent = value;
            list.append(dt, dd);
        }
        summary.appendChild(list);
    }

    async function run(action, successMessage, payload) {
        buttons.forEach(id => { $(id).disabled = true; });
        setStatus("Comunicando com o motor Python…");
        try {
            const result = await action(payload);
            setStatus(result.message || successMessage);
            showSummary(result);
        } catch (error) {
            setStatus("Não foi possível conectar ao backend Python: " + error.message, true);
        } finally {
            buttons.forEach(id => { $(id).disabled = false; });
        }
    }

    $("outbreak-start").addEventListener("click", () => {
        run(
            settings => window.Outbreak.start(settings),
            "Simulação iniciada.",
            { risk: $("outbreak-risk").value, seed: Number($("outbreak-seed").value) }
        );
    });
    $("outbreak-pause").addEventListener("click", () => run(() => window.Outbreak.pause(), "Simulação pausada."));
    $("outbreak-resume").addEventListener("click", () => run(() => window.Outbreak.resume(), "Simulação retomada."));
    $("outbreak-reset").addEventListener("click", () => {
        run(() => window.Outbreak.reset(), "Simulação reiniciada.");
        summary.replaceChildren();
    });

    window.OutbreakUI = Object.freeze({
        refresh: async () => {
            try {
                const result = await window.Outbreak.status();
                setStatus(result.message || (result.available ? "Backend Python conectado." : "Backend Python indisponível."));
                showSummary(result);
                return result;
            } catch (error) {
                setStatus("Backend Python ainda não conectado.", true);
                return null;
            }
        }
    });

    window.OutbreakUI.refresh();
})();
