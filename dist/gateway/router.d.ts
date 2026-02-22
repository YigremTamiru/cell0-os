import { InboundMessage, ChannelDomain } from '../channels/adapter.js';
export interface RouteDecision {
    domain: ChannelDomain;
    confidence: number;
    intent?: string;
    targetSpecialist?: string;
}
export declare class DomainRouter {
    /**
     * Determine the correct cognitive domain and specialist for an incoming message.
     * Evaluates explicit commands first, then falls back to the channel's default domain.
     * Future: Wrap col/classifier.py for deep semantic intent routing.
     */
    route(message: InboundMessage, defaultChannelDomain: ChannelDomain): Promise<RouteDecision>;
    private matchExplicitCommand;
}
//# sourceMappingURL=router.d.ts.map