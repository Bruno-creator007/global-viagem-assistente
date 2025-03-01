from flask_mail import Mail, Message
from flask import current_app
from datetime import datetime, timedelta

mail = Mail()

def send_email(to, subject, template):
    try:
        msg = Message(
            subject,
            recipients=[to],
            html=template,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {str(e)}")
        return False

def send_abandoned_cart_email(user_email):
    subject = "Não perca acesso ao seu Assistente de Viagem!"
    template = """
    <h2>Olá!</h2>
    <p>Notamos que você começou o processo de assinatura do nosso Assistente de Viagem, mas não completou.</p>
    <p>Com a assinatura, você terá acesso a:</p>
    <ul>
        <li>Planejamento personalizado de viagens</li>
        <li>Recomendações de lugares para visitar</li>
        <li>Dicas de restaurantes e atrações</li>
        <li>E muito mais!</li>
    </ul>
    <p><a href="https://pay.kiwify.com.br/Ug7fYhB">Clique aqui para completar sua assinatura</a></p>
    """
    return send_email(user_email, subject, template)

def send_subscription_expiring_email(user_email, days_remaining):
    subject = "Sua assinatura está próxima do vencimento"
    template = f"""
    <h2>Olá!</h2>
    <p>Sua assinatura do Assistente de Viagem vence em {days_remaining} dias.</p>
    <p>Para continuar tendo acesso a todas as funcionalidades, renove sua assinatura:</p>
    <p><a href="https://pay.kiwify.com.br/Ug7fYhB">Renovar agora</a></p>
    """
    return send_email(user_email, subject, template)

def send_payment_failed_email(user_email):
    subject = "Problema com seu pagamento"
    template = """
    <h2>Olá!</h2>
    <p>Identificamos um problema com seu último pagamento.</p>
    <p>Para evitar a interrupção do serviço, por favor, atualize suas informações de pagamento:</p>
    <p><a href="https://pay.kiwify.com.br/Ug7fYhB">Atualizar pagamento</a></p>
    """
    return send_email(user_email, subject, template)

def send_chargeback_notification_email(user_email):
    subject = "Notificação de Chargeback"
    template = """
    <h2>Olá!</h2>
    <p>Recebemos uma notificação de chargeback em sua assinatura.</p>
    <p>Por favor, entre em contato conosco para resolver esta situação:</p>
    <p>Email: suporte@globalviagem.com</p>
    """
    return send_email(user_email, subject, template)

def send_subscription_canceled_email(user_email):
    subject = "Sua assinatura foi cancelada"
    template = """
    <h2>Olá!</h2>
    <p>Sua assinatura do Assistente de Viagem foi cancelada.</p>
    <p>Sentiremos sua falta! Se quiser voltar a usar nossos serviços:</p>
    <p><a href="https://pay.kiwify.com.br/Ug7fYhB">Assinar novamente</a></p>
    """
    return send_email(user_email, subject, template)
