"""
These functions enable the front end to send information to where it's needed.
These functions were originally in views.py. 
"""

import json
import math
import sys

from flask import request

from simoc_server import app, db
from simoc_server.database.db_model import AgentType, AgentTypeAttribute, StorageCapacityRecord,\
    AgentTypeCountRecord


@app.route("/get_mass", methods=["GET"])
def get_mass():
    """
    Sends front end mass values for config wizard.
    Takes in the request values "agent_name" and "quantity"

    Returns
    -------
    json object with total mass
    """

    value = 0
    agent_name = request.args.get("agent_name", type=str)
    agent_quantity = request.args.get("quantity", type=int)
    if not agent_quantity:
        agent_quantity = 1
    if agent_name == "eclss":
        total = 0
        for agent in db.session.query(AgentType, AgentTypeAttribute).filter(AgentType.id == AgentTypeAttribute.agent_type_id).filter(AgentTypeAttribute.name == "char_mass").filter(AgentType.agent_class == "eclss").all():
            total += float(agent.AgentTypeAttribute.value)
        value = total
    else:
        for agent in db.session.query(AgentType, AgentTypeAttribute).filter(AgentType.id == AgentTypeAttribute.agent_type_id).filter(AgentTypeAttribute.name == "char_mass").all():
            if agent.AgentType.name == agent_name:
                value = float(agent.AgentTypeAttribute.value)
    value = value * agent_quantity
    total = { "mass" : value}
    return json.dumps(total)


@app.route("/get_energy", methods=["GET"])
def get_energy():
    """
    Sends front end energy values for config wizard.
    Takes in the request values "agent_name" and "quantity"

    Returns
    -------
    json object with energy value for agent
    """

    agent_name= request.args.get("agent_name", type=str)
    agent_quantity = request.args.get("quantity", type=int)
    attribute_name = "in_enrg_kwh"
    value_type = "energy_input"
    total = {}
    if not agent_quantity:
        agent_quantity = 1
    if agent_name == "eclss":
        total_eclss = 0
        for agent in db.session.query(AgentType, AgentTypeAttribute).filter(AgentType.id == AgentTypeAttribute.agent_type_id).filter(AgentTypeAttribute.name == "in_enrg_kwh").filter(AgentType.agent_class == "eclss").all():
            total_eclss += float(agent.AgentTypeAttribute.value)
        value = total_eclss * agent_quantity
        total = {value_type : value}
    else:
        if agent_name == "solar_pv_array_mars":
            attribute_name = "out_enrg_kwh"
            value_type = "energy_output"
        elif agent_name == "power_storage":
            attribute_name = "char_capacity_enrg_kwh"
            value_type = "energy_capacity"
        for agent in db.session.query(AgentType, AgentTypeAttribute).filter(AgentType.id == AgentTypeAttribute.agent_type_id).filter(AgentTypeAttribute.name == attribute_name).all():
            if agent.AgentType.name == agent_name:
                value = float(agent.AgentTypeAttribute.value) * agent_quantity
                total = { value_type : value}
    return json.dumps(total)


def convert_configuration(game_config):
    """This method converts the json configuration from a post into
    a more complete configuration with connections"""

    """THOMAS: This was created to allow the front end to send over a simplified version without connections. Connections are actually set up to connect to everything
    automatically, so this could use a re-haul. It also has some atmosphere values that are hard coded here that should be defined either in the agent library
    or sent from the front end. If this route is kept, most of the functionality should be moved into a separate object to help declutter and keep a solid separation
    of concerns. If it is removed, the data from the front end needs to be changed into a format based on an object similar to the one created here or in the new game view."""

    #Anything in this list will be copied as is from the input to the full_game_config. If it's not in the input it will be ignored
    labels_to_direct_copy = ["priorities","minutes_per_step","location"]
    #If a game_config element should be assigned as an agent with connections: power_storage only, add it to the list below (unless you want to rename the agent, then it will need it's own code)
    #Note, this assumes power_storage is the only connection for this agent. Do not add agents which have other connections. Only agents which are present in the input game_config will be assigned
    agents_to_assign_power_storage = ["habitat","greenhouse"]

    #Any agents with power_storage or food_storage will be assined power_storage = power_connections (defined later) etc. 
    #Agents initialised here must have all connections named here
    full_game_config = {"agents": {
        "human_agent":                            [
            {"connections": {"air_storage": [1], "water_storage": [1, 2], "food_storage": [1]}}],
        "solid_waste_aerobic_bioreactor":         [
            {"connections": {"air_storage":   [1], "power_storage": [1],
                             "water_storage": [1, 2], "nutrient_storage": [1]},
             "amount":      1}],
        "multifiltration_purifier_post_treament": [
            {"connections": {"water_storage": [1, 2], "power_storage": [1]}, "amount": 1}],
        "oxygen_generation_SFWE":                 [
            {"connections": {"air_storage": [1], "power_storage": [1], "water_storage": [1, 2]},
             "amount":      1}],
        "urine_recycling_processor_VCD":          [
            {"connections": {"power_storage": [1], "water_storage": [1, 2]}, "amount": 1}],
        "co2_removal_SAWD":                       [
            {"connections": {"air_storage": [1], "power_storage": [1]}, "amount": 1}],
        "co2_reduction_sabatier":                 [
            {"connections": {"air_storage": [1], "power_storage": [1], "water_storage": [1, 2]},
             "amount":      1}]
        # "particulate_removal_TCCS" : [{"connections":{"air_storage": [1],"power_storage": [1]},"amount":1}]
    },
        "storages":               {
            "air_storage": [
                {"id": 1, "atmo_h2o": 10, "atmo_o2": 2100, "atmo_co2": 3.5, "atmo_n2": 7886,
                 "atmo_ch4": 0.009531,
                 "atmo_h2": 0.005295}],
            "water_storage": [{"id": 1, "h2o_potb": 5000, "h2o_tret": 1000},
                              {"id": 2, "h2o_potb": 4000, "h2o_wste": 100, "h2o_urin": 100}],
            "nutrient_storage": [{"id": 1, "sold_n": 100, "sold_p": 100, "sold_k": 100}],
            "power_storage":    [],
            "food_storage":     []},
        "termination":            [
            {"condition": "evacuation"}]}
    food_storage_capacity = int(
        db.session.query(
            AgentType, AgentTypeAttribute).filter(
            AgentType.id == AgentTypeAttribute.agent_type_id).filter(
            AgentTypeAttribute.name == "char_capacity_food_edbl").first().AgentTypeAttribute.value)
    food_storage_amount = math.ceil(
        (game_config["food_storage"]["amount"]) / (int(food_storage_capacity)))


    #This is where labels from labels_to_direct_copy are copied directly from game_config to full_game_config
    for labeldc in labels_to_direct_copy:
        if labeldc in game_config:
            full_game_config[labeldc] = game_config[labeldc]

    #Assign termination values
    if ("duration" in game_config):
        duration = {
            "condition": "time",
            "value":     game_config["duration"]["value"],
            "unit":      game_config["duration"]["type"]}
        full_game_config["termination"].append(duration)

    #is it a single agent
    full_game_config["single_agent"] = 1 if ('single_agent' in game_config and game_config["single_agent"] == 1) else 0

    #The rest of this function is for reformatting agents.
    #food_connections and power_connections will be assigned to all agents with food_storage or power_storage respecitively, at the end of this function.

    #Determine the food and power connections to be assigned to all agents with food and power storage later
    power_storage_amount = game_config["power_storage"]["amount"]
    food_connections, power_connections = [], []
    food_left = game_config["food_storage"]["amount"]
    for x in range(1, int(food_storage_amount) + 1):
        food_connections.append(x)
        if (food_left > food_storage_capacity):
            full_game_config["storages"]["food_storage"].append(
                {"id": x, "food_edbl": food_storage_capacity})
            food_left -= food_storage_capacity
        else:
            full_game_config["storages"]["food_storage"].append(
                {"id": x, "food_edbl": food_left})

    for y in range(1, int(power_storage_amount) + 1):
        power_connections.append(y)
        full_game_config["storages"]["power_storage"].append(
            {"id": y, "enrg_kwh": 1000})


    #Here, agents from agents_to_assign_power_storage are assigned with only a power_storage connection.
    for labelps in agents_to_assign_power_storage:
        if (labelps in game_config):
            amount = 1 if not "amount" in game_config[labelps] else game_config[labelps]["amount"]
            full_game_config["agents"][game_config[labelps]] = [
                {"connections": {"power_storage": [1]}, "amount": amount}]


    #If you must rename it, it needs its own if statement.
    if ("solar_arrays" in game_config):
        full_game_config["agents"]["solar_pv_array_mars"] = [{"connections": {
            "power_storage": [1]}, "amount":                                 game_config[
                                                                                 "solar_arrays"][
                                                                                 "amount"]}]

    #If the front_end specifies an amount for this agent, overwrite any default values with the specified value
    for x, y in full_game_config["agents"].items():
        if x in game_config and "amount" in game_config[x]:
            y[0]["amount"] = game_config[x]["amount"]

    #Plants are treated separately because its a list of items which must be assigned as agents
    if "plants" in game_config:
        for plant in game_config["plants"]:
            full_game_config["agents"][plant["species"]] = [
                {"connections": {"air_storage": [1], "water_storage": [
                    1, 2], "nutrient_storage":  [1], "power_storage": [], "food_storage": [1]},
                 "amount":      plant["amount"]}]


    #Here, power connections and food connections are assigned to all agents with power_storage or food_storage specified. 
    for x, y in full_game_config["agents"].items():
        if "power_storage" in y[0]["connections"]:
            y[0]["connections"]["power_storage"] = power_connections
        if "food_storage" in y[0]["connections"]:
            y[0]["connections"]["food_storage"] = food_connections

    return full_game_config


def calc_step_in_out(direction, currencies, step_record_data):
    """ 
    Calculate the total production or total consumption of given currencies for a given step.

    Called from: route views.get_step()

    Input: direction "in" or "out" in=consumption, out=production
    currencies = list of currencies for which to calculate consumption or production. e.g. currencies = ["atmo_o2",""engr_kwh"]
    step_record_data = StepRecord for this step_num

    Output: dictionary of values and units for each currency. e.g. {"atmo_o2":{"value":0.05,"units":"kg"}}
    The unit is selected from the first currency, assuming all currencies with this name have the same units.

    """
    output = {}
    for currency in currencies:
        output[currency] = {'value': 0, 'unit': ''}

    for step in step_record_data:
        currency = step.currency_type.name
        if step.direction == direction and currency in output:
            output[currency]["value"] += step.value
            output[currency]["unit"] = step.unit

    return output


def calc_step_storage_ratios(agents, model_record_data):
    """ 
    Calculate the ratio for the requested currencies for the requested <agent_type>_<agent_id>.

    Called from: route views.get_step()

    Input: agents = dictionary of agents for which to calculate ratios. For each agent, give a list of the currencies which should be included in the output. e.g.{"air_storage_1":["atmo_co2"]}. step_record_data = StepRecord for this step_num.

    Output: dictionary of agents, each agent has a dictionary of currency:ratio pairs. e.g. {"air_storage_1": {"atmo_co2": 0.21001018914835098}
    """
    capacity_data = StorageCapacityRecord.query.filter_by(model_record=model_record_data).all()

    output = {}
    for agent in agents:
        agent_type = agent[:agent.rfind("_")]
        agent_id = int(agent[agent.rfind("_")+1:])
        capacities = [r for r in capacity_data
                      if r.agent_type.name == agent_type and r.storage_id == agent_id]

        # First, get sum of all currencies
        sum = 0
        unit = ""
        # for cap in capacities.all():
        for cap in capacities:
            sum += cap.value
            if unit == "":
                unit = cap.unit
            else:
                if not cap.unit == unit:
                    sys.exit("ERROR in front_end_routes.calc_step_storage_ratios()."
                             "Currencies do not have same units.", unit, cap.unit)

        output[agent] = {}
        # Now, calculate the ratio for specified currencies.
        for currency in agents[agent]:
            c_step_data = [r for r in capacities if r.currency_type.name == currency][0]
            output[agent][currency] = c_step_data.value / sum

    return output


def parse_step_data(model_record_data, filters, step_record_data):
    reduced_output = model_record_data.get_data()
    if len(filters) == 0:
        return reduced_output
    for f in filters:
        if f == "agent_type_counters":
            reduced_output[f] = [i.get_data() for i in model_record_data.agent_type_counters]
        if f == "agent_type_counters":
            reduced_output[f] = [i.get_data() for i in model_record_data.storage_capacities]
        if f == "agent_logs":
            reduced_output[f] = [i.get_data() for i in step_record_data.all()]
        else:
            print(f"WARNING: No parse_filters option {filter} in game_runner.parse_step_data.")
    return reduced_output


def count_agents_in_step(agent_types, model_record_data):
    """ 
    Count the number of agents matching the agent_name for this step

    Called from: route views.get_step()

    Input: agent_names, step_record_data

    Output: dictionary of counts for each agent names {"human_agent":count}

    """
    output = {}
    for agent_type in agent_types:
        output[agent_type] = 0

    agent_counters = AgentTypeCountRecord.query.filter_by(model_record=model_record_data).all()
    for record in agent_counters:
        if record.agent_type.name in output:
            output[record.agent_type.name] += record.agent_counter

    return output


def sum_agent_values_in_step(agent_types, currency_type_name, direction, step_record_data):
    """ 
    Sum the values for this agent

    Called from: route views.get_step()

    Input: agent_names, step_record_data

    Output: dictionary of sum of values and units for each agent names {"rice":{"value": value, "unit": unit}}

    """

    output = {}
    for agent_type in agent_types:
        output[agent_type] = {'value': 0, 'unit': ''}

    for step in step_record_data:
        agent_type = step.agent_type.name
        if (step.currency_type.name == currency_type_name
                and step.direction == direction and agent_type in output):
            output[agent_type]["value"] += step.value
            output[agent_type]["unit"] = step.unit

    return output


def calc_step_storage_capacities(agents, model_record_data):

    output = {}
    for agent_id in agents:
        output[agent_id] = {currency: {'value': 0, 'unit': ''}
                            for currency in agents[agent_id]}

    storage_capacities = StorageCapacityRecord.query \
        .filter_by(model_record=model_record_data).all()

    for record in storage_capacities:
        agent_type = record.agent_type.name
        storage_id = record.storage_id
        agent_id = f'{agent_type}_{storage_id}'
        currency = record.currency_type.name
        if agent_id in output and currency in output[agent_id]:
            output[agent_id][currency]['value'] = record.value
            output[agent_id][currency]['unit'] = record.unit

    return output
