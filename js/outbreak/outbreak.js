/* outbreak.js — cliente de comunicação com o backend Python do Outbreak Engine.
 * O motor Python é a fonte da simulação; este arquivo não reimplementa sua lógica.
 */
(() => {
    "use strict";

    const DEFAULT_BASE_URL = "/api/outbreak";
    let baseUrl = DEFAULT_BASE_URL;

    async function request(path, options = {}) {
        const response = await fetch(baseUrl + path, {
            headers: { "Content-Type": "application/json", ...(options.headers || {}) },
            ...options
        });

        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(body.error || body.message || `Erro HTTP ${response.status}`);
        }
        return body;
    }

    window.Outbreak = Object.freeze({
        configure(url) {
            baseUrl = String(url || DEFAULT_BASE_URL).replace(/\/+$/, "");
        },
        get baseUrl() {
            return baseUrl;
        },
        status() {
            return request("/status");
        },
        start(settings = {}) {
            return request("/start", {
                method: "POST",
                body: JSON.stringify(settings)
            });
        },
        pause() {
            return request("/pause", { method: "POST", body: "{}" });
        },
        resume() {
            return request("/resume", { method: "POST", body: "{}" });
        },
        reset() {
            return request("/reset", { method: "POST", body: "{}" });
        },
        state() {
            return request("/state");
        }
    });
})();
