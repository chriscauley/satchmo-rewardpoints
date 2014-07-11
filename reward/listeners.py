import math

from livesettings import config_value
from satchmo_store.shop.models import Order
from django.utils.translation import ugettext as _

from reward.models import Reward, RewardItem, POINTS_PENDING, POINTS_ADDED, POINTS_DEDUCTED

import logging, sys, traceback

log = logging.getLogger('rewards.listeners')


def create_reward(contact, subscribed):
    """
    On creation of a customer account create rewards for them and add intial points if any.
    """
    log.debug("Caught registration, adding reward and initial customer points.")
    init_points = config_value('PAYMENT_REWARD', 'INITIAL_POINTS')
    reward = Reward.objects.create(contact=contact)
    if init_points > 0:
        point_item = RewardItem.objects.create(
            reward=reward, 
            points=init_points, 
            transaction_description="Initial Points", 
            status=POINTS_ADDED,
        )
        
def create_reward_listener(contact=None, subscribed=False, **kwargs):
    if contact:
        create_reward(contact, subscribed)
        

def add_points_on_order(order=None, **kwargs):
    log.debug("Caught order, attempting to add customer points pending.")
    if order:
        if order.contact.user:
            if not RewardItem.objects.filter(order=order).filter(status=POINTS_PENDING).exists():
                reward = Reward.objects.get_or_create(contact=order.contact)
                points = math.floor(order.total * config_value('PAYMENT_REWARD', 'POINTS_EARNT') /100)
                log.debug("Gave %s %s pending points for order #%s"%(order.contact.user,points,order.id))
                description = _('Points earned from Order #%s'%order.id)
                RewardItem.objects.update_or_create(order.contact,order,points,POINTS_PENDING,description)

def remove_points(order,oldstatus=None):
    log.debug("Caught order cancelled, attempting to remove customer points.")
    item = RewardItem.objects.get(order=order,orderpayment=None)
    if item:
        if oldstatus == "Complete":
            item.reward.points = item.reward.points - item.points
            item.reward.save()
        item.delete()
        
            
def add_points_on_complete(order):
    try:
        item = RewardItem.objects.get(order=order)
    except RewardItem.DoesNotExist:
        points = math.floor(order.total * config_value('PAYMENT_REWARD', 'POINTS_EARNT') /100)
        description = _('Points earned from Order #%s'%order.id)
        item = RewardItem.objects.update_or_create(order.contact,order,points,POINTS_ADDED,description)
    except Execption,err:
        log.debug("Can't change status of points")
        log.debug(traceback.format_exc())
        return
    if item.status != POINTS_ADDED:
        item.status = POINTS_ADDED
        item.save()
        reward = item.reward
        reward.points = item.reward.points + item.points
        log.debug("Added points to order #%s"%order.id)
        reward.save()
            
def rcv_order_status_changed(oldstatus=None, newstatus=None, order=None, **kwargs):
    if order:
        if newstatus == "Complete":
            add_points_on_complete(order)
        if newstatus == "Cancelled":
            remove_points(order,oldstatus)
