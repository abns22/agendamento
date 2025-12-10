"""
Serviço de Validação de Promoções.

Este serviço implementa a lógica de validação de promoções ativas,
verificando se uma promoção está dentro do período válido.
"""
from datetime import datetime, timezone
from typing import Optional, Tuple
from app.models.service import Service


class PromotionService:
    """
    Serviço responsável por validar e processar promoções de serviços.
    """
    
    @staticmethod
    def is_promotion_active(service: Service) -> Tuple[bool, Optional[float]]:
        """
        Verifica se uma promoção está ativa no momento atual.
        
        Uma promoção é considerada ativa se:
        1. is_promotional for True
        2. A data/hora atual estiver dentro do intervalo [promotion_start_date, promotion_end_date]
        
        Args:
            service: Objeto Service com dados de promoção
            
        Returns:
            Tuple[bool, Optional[float]]: 
            - (True, promotional_value) se a promoção estiver ativa
            - (False, None) se a promoção não estiver ativa ou não existir
        """
        # Se não for promocional, retornar False
        if not service.is_promotional:
            return False, None
        
        # Se não tiver datas de início e fim, considerar inativa
        if not service.promotion_start_date or not service.promotion_end_date:
            return False, None
        
        # Obter data/hora atual em UTC
        now_utc = datetime.now(timezone.utc)
        
        # Garantir que as datas de promoção estão em UTC (timezone-aware)
        start_date = service.promotion_start_date
        end_date = service.promotion_end_date
        
        # Se as datas não tiverem timezone, assumir UTC
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Verificar se a data atual está dentro do intervalo
        if start_date <= now_utc <= end_date:
            # Promoção ativa: retornar True e o valor promocional
            promotional_value = float(service.promotional_value) if service.promotional_value else None
            return True, promotional_value
        else:
            # Promoção expirada ou ainda não iniciada
            return False, None
    
    @staticmethod
    def get_effective_price(service: Service) -> float:
        """
        Retorna o preço efetivo do serviço (promocional se ativo, senão preço normal).
        
        Args:
            service: Objeto Service
            
        Returns:
            float: Preço efetivo (promocional se ativo, senão preço normal)
        """
        is_active, promotional_value = PromotionService.is_promotion_active(service)
        
        if is_active and promotional_value is not None:
            return promotional_value
        else:
            return float(service.price)
    
    @staticmethod
    def get_promotion_data(service: Service) -> Optional[dict]:
        """
        Retorna os dados da promoção se estiver ativa, senão None.
        
        Args:
            service: Objeto Service
            
        Returns:
            Optional[dict]: Dados da promoção se ativa, None caso contrário
        """
        is_active, promotional_value = PromotionService.is_promotion_active(service)
        
        if not is_active:
            return None
        
        return {
            "is_active": True,
            "promotional_value": promotional_value,
            "original_price": float(service.price),
            "display_name": service.promotion_display_name,
            "description": service.promotion_description,
            "color_code": service.promotion_color_code,
            "start_date": service.promotion_start_date.isoformat() if service.promotion_start_date else None,
            "end_date": service.promotion_end_date.isoformat() if service.promotion_end_date else None
        }

