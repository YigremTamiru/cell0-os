/**
 * Cell 0 OS — Tailscale Tunneling
 *
 * Native integration with the Tailscale CLI bounds.
 * Allows instant secure port-forwardless ingress into the OS Gateway.
 */
export declare class TailscaleManager {
    /**
     * Initiates a `tailscale serve` or `tailscale funnel` binding
     * the local Cell 0 OS Gateway to a secure public URL.
     */
    expose(port: number, useFunnel?: boolean): Promise<string>;
}
//# sourceMappingURL=tailscale.d.ts.map