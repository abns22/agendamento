"""
Serviço de integração com WhatsApp (Meta Cloud API).

Este serviço é responsável por enviar notificações via WhatsApp
usando a API do Meta (WhatsApp Business Cloud API).
"""
from uuid import UUID
from app.core.config import settings
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Serviço para envio de mensagens via WhatsApp Business Cloud API.
    """
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    @staticmethod
    async def send_appointment_notification(
        phone_number_id: str,
        customer_phone: str,
        customer_name: str,
        appointment_datetime: str,
        service_name: str
    ) -> bool:
        """
        Envia notificação de confirmação de agendamento via WhatsApp.
        
        IMPORTANTE: Esta função deve usar Templates aprovados pela Meta.
        Não é possível enviar mensagens livres no início de uma conversa.
        
        Args:
            phone_number_id: ID do número de telefone do WhatsApp Business
            customer_phone: Telefone do cliente (formato internacional, ex: 5511999999999)
            customer_name: Nome do cliente
            appointment_datetime: Data e hora do agendamento formatada
            service_name: Nome do serviço agendado
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        if not settings.WHATSAPP_ACCESS_TOKEN:
            logger.warning("WhatsApp access token não configurado. Notificação não enviada.")
            return False
        
        if not phone_number_id:
            logger.warning("WhatsApp phone number ID não configurado. Notificação não enviada.")
            return False
        
        try:
            # Formatar telefone (remover caracteres não numéricos e adicionar código do país se necessário)
            formatted_phone = ''.join(filter(str.isdigit, customer_phone))
            if not formatted_phone.startswith('55'):  # Código do Brasil
                formatted_phone = f"55{formatted_phone}"
            
            # URL da API do WhatsApp
            url = f"{WhatsAppService.BASE_URL}/{phone_number_id}/messages"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Corpo da mensagem usando Template Message
            # NOTA: Você precisa criar um template aprovado no Meta Business Manager
            # Este é um exemplo genérico - ajuste conforme seu template aprovado
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": "template",
                "template": {
                    "name": "appointment_confirmation",  # Nome do template aprovado
                    "language": {
                        "code": "pt_BR"
                    },
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text",
                                    "text": customer_name
                                },
                                {
                                    "type": "text",
                                    "text": service_name
                                },
                                {
                                    "type": "text",
                                    "text": appointment_datetime
                                }
                            ]
                        }
                    ]
                }
            }
            
            # Enviar requisição
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                logger.info(f"Notificação WhatsApp enviada para {customer_phone}")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar notificação WhatsApp: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar notificação WhatsApp: {str(e)}")
            return False
    
    @staticmethod
    async def send_new_appointment_alert(
        phone_number_id: str,
        tenant_phone_number: str,
        customer_name: str,
        appointment_time: str,
        service_name: str
    ) -> bool:
        """
        Envia alerta de novo agendamento para o estúdio via WhatsApp.
        
        IMPORTANTE: Este método usa mensagem de texto livre (não template),
        pois o estúdio é um destinatário que já iniciou a conversa ou tem
        a conversa aberta. Isso permite o uso de mensagens que não são Template.
        
        O número de destino (tenant_phone_number) deve vir do objeto Tenant
        do banco de dados (o número que a empresa cadastrou para receber notificações).
        
        Args:
            phone_number_id: ID do número de telefone do WhatsApp Business (do Tenant)
            tenant_phone_number: Número de telefone do estúdio (formato internacional, ex: 5511999999999)
            customer_name: Nome do cliente que fez o agendamento
            appointment_time: Data e hora do agendamento formatada (ex: "25/12/2024 às 14:30")
            service_name: Nome do serviço agendado
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        if not settings.WHATSAPP_ACCESS_TOKEN:
            logger.warning("WhatsApp access token não configurado. Alerta não enviado.")
            return False
        
        if not phone_number_id:
            logger.warning("WhatsApp phone number ID não configurado. Alerta não enviado.")
            return False
        
        if not tenant_phone_number:
            logger.warning("Número de telefone do tenant não fornecido. Alerta não enviado.")
            return False
        
        try:
            # Formatar telefone do estúdio (remover caracteres não numéricos e adicionar código do país se necessário)
            formatted_phone = ''.join(filter(str.isdigit, tenant_phone_number))
            if not formatted_phone.startswith('55'):  # Código do Brasil
                formatted_phone = f"55{formatted_phone}"
            
            # URL da API do WhatsApp
            url = f"{WhatsAppService.BASE_URL}/{phone_number_id}/messages"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Construir mensagem informativa e urgente
            message_body = (
                f"🚨 NOVO AGENDAMENTO! 🚨\n\n"
                f"Cliente: {customer_name}\n"
                f"Serviço: {service_name}\n"
                f"Horário: {appointment_time}\n"
                f"Status: Pendente"
            )
            
            # Corpo da mensagem usando Text Message (mensagem livre)
            # IMPORTANTE: Só funciona se o estúdio já iniciou a conversa ou tem a conversa aberta
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }
            
            # Enviar requisição
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                logger.info(f"Alerta de novo agendamento enviado para estúdio: {tenant_phone_number}")
                return True
                
        except httpx.HTTPStatusError as e:
            # Log detalhado do erro da API
            error_detail = ""
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = f" - {error_data}"
                except:
                    error_detail = f" - Status: {e.response.status_code}"
            
            logger.error(f"Erro HTTP ao enviar alerta WhatsApp para estúdio: {str(e)}{error_detail}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"Erro de conexão ao enviar alerta WhatsApp: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar alerta WhatsApp: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    async def send_cancellation_notification(
        phone_number_id: str,
        customer_phone: str,
        customer_name: str,
        appointment_datetime: str,
        service_name: str,
        cancellation_reason: str
    ) -> bool:
        """
        Envia notificação de cancelamento de agendamento via WhatsApp.
        
        IMPORTANTE: Esta função usa mensagem de texto livre (não template),
        pois o cliente já iniciou a conversa ao fazer o agendamento.
        Isso permite o uso de mensagens que não são Template.
        
        Args:
            phone_number_id: ID do número de telefone do WhatsApp Business
            customer_phone: Telefone do cliente (formato internacional, ex: 5511999999999)
            customer_name: Nome do cliente
            appointment_datetime: Data e hora do agendamento formatada
            service_name: Nome do serviço agendado
            cancellation_reason: Motivo do cancelamento fornecido pelo tenant
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        if not settings.WHATSAPP_ACCESS_TOKEN:
            logger.warning("WhatsApp access token não configurado. Notificação de cancelamento não enviada.")
            return False
        
        if not phone_number_id:
            logger.warning("WhatsApp phone number ID não configurado. Notificação de cancelamento não enviada.")
            return False
        
        try:
            # Formatar telefone (remover caracteres não numéricos e adicionar código do país se necessário)
            formatted_phone = ''.join(filter(str.isdigit, customer_phone))
            if not formatted_phone.startswith('55'):  # Código do Brasil
                formatted_phone = f"55{formatted_phone}"
            
            # URL da API do WhatsApp
            url = f"{WhatsAppService.BASE_URL}/{phone_number_id}/messages"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Construir mensagem de cancelamento
            message_body = (
                f"❌ Agendamento Cancelado\n\n"
                f"Olá {customer_name},\n\n"
                f"Infelizmente, seu agendamento foi cancelado.\n\n"
                f"📅 Serviço: {service_name}\n"
                f"🕐 Horário: {appointment_datetime}\n\n"
                f"Motivo do cancelamento:\n{cancellation_reason}\n\n"
                f"Por favor, entre em contato conosco para reagendar, se desejar.\n\n"
                f"Desculpe pelo inconveniente."
            )
            
            # Corpo da mensagem usando Text Message (mensagem livre)
            # IMPORTANTE: Só funciona se o cliente já iniciou a conversa ou tem a conversa aberta
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }
            
            # Enviar requisição
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                logger.info(f"Notificação de cancelamento WhatsApp enviada para {customer_phone}")
                return True
                
        except httpx.HTTPStatusError as e:
            # Log detalhado do erro da API
            error_detail = ""
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = f" - {error_data}"
                except:
                    error_detail = f" - Status: {e.response.status_code}"
            
            logger.error(f"Erro HTTP ao enviar notificação de cancelamento WhatsApp: {str(e)}{error_detail}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"Erro de conexão ao enviar notificação de cancelamento WhatsApp: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar notificação de cancelamento WhatsApp: {str(e)}", exc_info=True)
            return False


