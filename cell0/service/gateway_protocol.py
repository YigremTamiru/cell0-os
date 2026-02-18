"""
gateway_protocol.py - JSON-RPC Protocol Handlers for Cell 0 OS Gateway

Implements JSON-RPC 2.0 protocol for WebSocket communication.
Provides request/response handling, notifications, batch requests,
and protocol extensions for real-time event streaming.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import traceback

logger = logging.getLogger("cell0.gateway.protocol")


class JsonRpcErrorCode(Enum):
    """JSON-RPC 2.0 error codes"""
    # Standard errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # Server errors (reserved range -32000 to -32099)
    SERVER_ERROR = -32000
    AUTHENTICATION_ERROR = -32001
    AUTHORIZATION_ERROR = -32002
    RATE_LIMIT_ERROR = -32003
    TIMEOUT_ERROR = -32004
    
    # Application errors
    SESSION_ERROR = -32100
    ENTITY_NOT_FOUND = -32101
    INVALID_STATE = -32102
    ROUTING_ERROR = -32103


class GatewayError(Exception):
    """Base exception for gateway errors"""
    def __init__(
        self,
        code: JsonRpcErrorCode,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.data = data or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        error = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.data:
            error["data"] = self.data
        return error


class AuthenticationError(GatewayError):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication failed", data: Optional[Dict] = None):
        super().__init__(JsonRpcErrorCode.AUTHENTICATION_ERROR, message, data)


class AuthorizationError(GatewayError):
    """Not authorized for operation"""
    def __init__(self, message: str = "Not authorized", data: Optional[Dict] = None):
        super().__init__(JsonRpcErrorCode.AUTHORIZATION_ERROR, message, data)


class MethodNotFoundError(GatewayError):
    """Method not found"""
    def __init__(self, method: str):
        super().__init__(
            JsonRpcErrorCode.METHOD_NOT_FOUND,
            f"Method not found: {method}",
            {"method": method}
        )


class InvalidParamsError(GatewayError):
    """Invalid parameters"""
    def __init__(self, message: str = "Invalid params", data: Optional[Dict] = None):
        super().__init__(JsonRpcErrorCode.INVALID_PARAMS, message, data)


@dataclass
class JsonRpcRequest:
    """JSON-RPC request object"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None
    
    # Extension fields for Cell 0 OS
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_notification(self) -> bool:
        """Check if this is a notification (no id)"""
        return self.id is None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JsonRpcRequest':
        """Create from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result


@dataclass
class JsonRpcResponse:
    """JSON-RPC response object"""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    # Extension fields
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error response"""
        return self.error is not None
    
    @classmethod
    def success(
        cls,
        id: Union[str, int],
        result: Any
    ) -> 'JsonRpcResponse':
        """Create a success response"""
        return cls(jsonrpc="2.0", result=result, id=id)
    
    @classmethod
    def error(
        cls,
        id: Optional[Union[str, int]],
        code: int,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> 'JsonRpcResponse':
        """Create an error response"""
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
        return cls(jsonrpc="2.0", error=error, id=id)
    
    @classmethod
    def from_exception(
        cls,
        id: Optional[Union[str, int]],
        exc: Exception
    ) -> 'JsonRpcResponse':
        """Create an error response from an exception"""
        if isinstance(exc, GatewayError):
            return cls.error(id, exc.code.value, exc.message, exc.data)
        
        return cls.error(
            id,
            JsonRpcErrorCode.INTERNAL_ERROR.value,
            str(exc) or "Internal error",
            {"traceback": traceback.format_exc()} if logger.isEnabledFor(logging.DEBUG) else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {"jsonrpc": self.jsonrpc}
        if self.error:
            result["error"] = self.error
        else:
            result["result"] = self.result
        if self.id is not None:
            result["id"] = self.id
        return result


@dataclass
class JsonRpcNotification:
    """JSON-RPC notification (server -> client)"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    
    # Extension for event streaming
    event_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params:
            result["params"] = self.params
        return result
    
    @classmethod
    def event(
        cls,
        event_type: str,
        data: Dict[str, Any],
        source: Optional[str] = None
    ) -> 'JsonRpcNotification':
        """Create an event notification"""
        return cls(
            method="event",
            params={
                "type": event_type,
                "data": data,
                "source": source,
                "timestamp": datetime.utcnow().isoformat(),
            },
            event_type=event_type
        )


class MethodRegistry:
    """Registry for JSON-RPC methods"""
    
    def __init__(self):
        self._methods: Dict[str, Dict] = {}
        self._middleware: List[Callable] = []
    
    def register(
        self,
        name: str,
        handler: Optional[Callable] = None,
        require_auth: bool = True,
        required_permissions: Optional[List[str]] = None
    ):
        """Register a method handler. Can be used as decorator or direct call."""
        def decorator(func: Callable) -> Callable:
            self._methods[name] = {
                "handler": func,
                "require_auth": require_auth,
                "required_permissions": required_permissions or [],
            }
            logger.debug(f"Registered method: {name}")
            return func
        
        if handler is not None:
            # Direct call: register(name, handler_func)
            return decorator(handler)
        else:
            # Decorator usage: @register(name)
            return decorator
    
    def unregister(self, name: str):
        """Unregister a method"""
        if name in self._methods:
            del self._methods[name]
    
    def add_middleware(self, middleware: Callable):
        """Add middleware for method calls"""
        self._middleware.append(middleware)
    
    def get_method(self, name: str) -> Optional[Dict]:
        """Get method info by name"""
        return self._methods.get(name)
    
    def list_methods(self) -> List[str]:
        """List all registered method names"""
        return list(self._methods.keys())
    
    async def execute(
        self,
        request: JsonRpcRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> JsonRpcResponse:
        """Execute a method call"""
        context = context or {}
        
        # Find method
        method_info = self.get_method(request.method)
        if not method_info:
            raise MethodNotFoundError(request.method)
        
        # Check authentication
        if method_info["require_auth"]:
            session = context.get("session")
            if not session or not session.authenticated:
                raise AuthenticationError("Authentication required")
        
        # Check permissions
        if method_info["required_permissions"]:
            session = context.get("session")
            for perm in method_info["required_permissions"]:
                if not session or not session.has_permission(perm):
                    raise AuthorizationError(f"Missing permission: {perm}")
        
        # Apply middleware
        for middleware in self._middleware:
            result = await middleware(request, context)
            if isinstance(result, JsonRpcResponse):
                return result
        
        # Execute handler
        handler = method_info["handler"]
        
        # Build arguments
        kwargs = {"context": context}
        if request.params:
            if isinstance(request.params, dict):
                kwargs.update(request.params)
            elif isinstance(request.params, list):
                # Positional arguments not supported, convert to kwargs
                raise InvalidParamsError("Named parameters required")
        
        # Call handler
        if asyncio.iscoroutinefunction(handler):
            result = await handler(**kwargs)
        else:
            result = handler(**kwargs)
        
        return JsonRpcResponse.success(request.id, result)


class ProtocolHandler:
    """
    Main protocol handler for JSON-RPC over WebSocket.
    Manages request/response lifecycle and batch processing.
    """
    
    def __init__(self, method_registry: Optional[MethodRegistry] = None):
        self.registry = method_registry or MethodRegistry()
        self._request_handlers: Dict[str, Callable] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        
        # Statistics
        self.stats = {
            "requests_processed": 0,
            "notifications_received": 0,
            "errors": 0,
            "batches_processed": 0,
        }
    
    async def handle_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Union[JsonRpcResponse, List[JsonRpcResponse]]]:
        """
        Handle an incoming message.
        Returns response(s) or None for notifications.
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            self.stats["errors"] += 1
            return JsonRpcResponse.error(
                None,
                JsonRpcErrorCode.PARSE_ERROR.value,
                f"Parse error: {e}"
            )
        
        # Handle batch requests
        if isinstance(data, list):
            if not data:
                self.stats["errors"] += 1
                return JsonRpcResponse.error(
                    None,
                    JsonRpcErrorCode.INVALID_REQUEST.value,
                    "Invalid batch: empty array"
                )
            
            self.stats["batches_processed"] += 1
            responses = []
            for item in data:
                response = await self._handle_single(item, context)
                if response:  # Don't include None responses (notifications)
                    responses.append(response)
            
            return responses if responses else None
        
        # Handle single request
        return await self._handle_single(data, context)
    
    async def _handle_single(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[JsonRpcResponse]:
        """Handle a single request/notification"""
        # Validate JSON-RPC version
        if data.get("jsonrpc") != "2.0":
            self.stats["errors"] += 1
            return JsonRpcResponse.error(
                data.get("id"),
                JsonRpcErrorCode.INVALID_REQUEST.value,
                "Invalid JSON-RPC version"
            )
        
        # Check for method
        if "method" not in data:
            self.stats["errors"] += 1
            return JsonRpcResponse.error(
                data.get("id"),
                JsonRpcErrorCode.INVALID_REQUEST.value,
                "Missing method"
            )
        
        # Create request object
        try:
            request = JsonRpcRequest.from_dict(data)
            if context and "session_id" in context:
                request.session_id = context["session_id"]
        except Exception as e:
            self.stats["errors"] += 1
            return JsonRpcResponse.error(
                data.get("id"),
                JsonRpcErrorCode.INVALID_REQUEST.value,
                f"Invalid request: {e}"
            )
        
        # Handle notification (no id)
        if request.is_notification:
            self.stats["notifications_received"] += 1
            asyncio.create_task(self._handle_notification(request, context))
            return None
        
        # Handle request
        self.stats["requests_processed"] += 1
        return await self._handle_request(request, context)
    
    async def _handle_request(
        self,
        request: JsonRpcRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> JsonRpcResponse:
        """Handle a request and return response"""
        try:
            response = await self.registry.execute(request, context)
            return response
        except GatewayError as e:
            self.stats["errors"] += 1
            return JsonRpcResponse.from_exception(request.id, e)
        except Exception as e:
            self.stats["errors"] += 1
            logger.exception(f"Error handling request {request.method}: {e}")
            return JsonRpcResponse.from_exception(request.id, e)
    
    async def _handle_notification(
        self,
        request: JsonRpcRequest,
        context: Optional[Dict[str, Any]] = None
    ):
        """Handle a notification (fire and forget)"""
        try:
            # Some notifications are handled specially
            if request.method == "heartbeat":
                await self._handle_heartbeat(request, context)
            elif request.method == "presence.update":
                await self._handle_presence_update(request, context)
            else:
                # Try to execute as method
                await self.registry.execute(request, context)
        except Exception as e:
            logger.debug(f"Notification handler error (ignored): {e}")
    
    async def _handle_heartbeat(
        self,
        request: JsonRpcRequest,
        context: Optional[Dict[str, Any]] = None
    ):
        """Handle heartbeat notification"""
        if context and "session" in context:
            session = context["session"]
            session.touch()
            
            # Update presence
            from service.presence import presence_manager
            await presence_manager.touch_presence(session.entity_id)
    
    async def _handle_presence_update(
        self,
        request: JsonRpcRequest,
        context: Optional[Dict[str, Any]] = None
    ):
        """Handle presence update notification"""
        from service.presence import presence_manager, PresenceStatus
        
        params = request.params or {}
        entity_id = params.get("entity_id")
        status = params.get("status", "online")
        
        if entity_id:
            await presence_manager.update_presence(
                entity_id=entity_id,
                status=PresenceStatus(status),
                status_message=params.get("status_message"),
                current_activity=params.get("activity"),
                metadata_updates=params.get("metadata")
            )
    
    def create_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> JsonRpcNotification:
        """Create a notification message"""
        return JsonRpcNotification(method=method, params=params)
    
    def create_event_notification(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: Optional[str] = None
    ) -> JsonRpcNotification:
        """Create an event notification"""
        return JsonRpcNotification.event(event_type, data, source)


# Built-in protocol methods

def register_builtin_methods(registry: MethodRegistry):
    """Register built-in JSON-RPC methods"""
    
    @registry.register("rpc.listMethods", require_auth=False)
    async def list_methods(context=None, **kwargs) -> List[str]:
        """List available RPC methods"""
        return registry.list_methods()
    
    @registry.register("rpc.getMethodInfo", require_auth=False)
    async def get_method_info(method: str, context=None, **kwargs) -> Dict[str, Any]:
        """Get information about a method"""
        method_info = registry.get_method(method)
        if not method_info:
            raise MethodNotFoundError(method)
        
        return {
            "name": method,
            "require_auth": method_info["require_auth"],
            "required_permissions": method_info["required_permissions"],
        }
    
    @registry.register("rpc.ping", require_auth=False)
    async def ping(context=None, **kwargs) -> str:
        """Ping the server"""
        return "pong"
    
    @registry.register("rpc.echo", require_auth=False)
    async def echo(message: str, context=None, **kwargs) -> str:
        """Echo a message back"""
        return message
    
    @registry.register("rpc.getServerInfo", require_auth=False)
    async def get_server_info(context=None, **kwargs) -> Dict[str, Any]:
        """Get server information"""
        return {
            "name": "Cell 0 OS Gateway",
            "version": "1.0.0",
            "jsonrpc_version": "2.0",
            "capabilities": [
                "jsonrpc_2.0",
                "batch_requests",
                "notifications",
                "event_streaming",
                "presence",
                "multi_agent_routing",
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @registry.register("rpc.getStats", require_auth=True)
    async def get_stats(context=None, **kwargs) -> Dict[str, Any]:
        """Get gateway statistics"""
        from service.gateway_protocol import protocol_handler
        return protocol_handler.stats


# Global protocol handler instance
protocol_handler = ProtocolHandler()
register_builtin_methods(protocol_handler.registry)


def create_error_response(
    code: JsonRpcErrorCode,
    message: str,
    id: Optional[Union[str, int]] = None,
    data: Optional[Dict[str, Any]] = None
) -> JsonRpcResponse:
    """Create an error response"""
    return JsonRpcResponse.error(id, code.value, message, data)
