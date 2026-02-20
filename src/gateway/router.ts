import { InboundMessage, ChannelDomain } from '../channels/adapter.js';

export interface RouteDecision {
    domain: ChannelDomain;
    confidence: number;
    intent?: string;
    targetSpecialist?: string;
}

export class DomainRouter {
    /**
     * Determine the correct cognitive domain and specialist for an incoming message.
     * Evaluates explicit commands first, then falls back to the channel's default domain.
     * Future: Wrap col/classifier.py for deep semantic intent routing.
     */
    public async route(message: InboundMessage, defaultChannelDomain: ChannelDomain): Promise<RouteDecision> {
        const text = message.text?.trim() || '';

        // 1. Explicit Domain Commands (e.g., "/finance What is the stock price?")
        const explicitMatch = this.matchExplicitCommand(text);
        if (explicitMatch) {
            return {
                domain: explicitMatch.domain,
                confidence: 1.0,
                intent: 'explicit_command'
            };
        }

        // 2. Semantic Intent Scoring (Placeholder for col/classifier.py IPC)
        // For now, we fallback to the channel's native default domain

        return {
            domain: defaultChannelDomain,
            confidence: 0.5,
            intent: 'implicit_channel_default'
        };
    }

    private matchExplicitCommand(text: string): { domain: ChannelDomain } | null {
        if (text.startsWith('/social')) return { domain: 'social' };
        if (text.startsWith('/prod') || text.startsWith('/productivity')) return { domain: 'productivity' };
        if (text.startsWith('/finance')) return { domain: 'finance' };
        if (text.startsWith('/travel')) return { domain: 'travel' };
        if (text.startsWith('/creative') || text.startsWith('/creativity')) return { domain: 'creativity' };
        if (text.startsWith('/info') || text.startsWith('/information')) return { domain: 'information' };
        if (text.startsWith('/util') || text.startsWith('/utilities')) return { domain: 'utilities' };
        if (text.startsWith('/system')) return { domain: 'system' };

        return null;
    }
}
