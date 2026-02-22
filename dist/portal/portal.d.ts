/**
 * Cell 0 OS — Nerve Portal
 *
 * The portal is the nervous system's output. When a user opens
 * http://127.0.0.1:18790 they see a kernel boot sequence, then
 * a full-width Quick Chat with a floating Glassbox assistive touch bubble.
 *
 * Tabs: Chat | Monitor (htop) | Nerve Map | Config | Agent Library
 * Port: 18790 (separate from gateway 18789)
 */
import http from "node:http";
export interface PortalConfig {
    port: number;
    host: string;
    gatewayPort: number;
    gatewayToken?: string;
}
export declare function startPortal(config?: Partial<PortalConfig>): Promise<http.Server>;
//# sourceMappingURL=portal.d.ts.map