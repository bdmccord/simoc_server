import math
import datetime

from simoc_server.agent_model.agents.core import EnclosedAgent
from simoc_server.util import timedelta_to_days, timedelta_hour_of_day
from simoc_server.exceptions import AgentModelError

# metabolism_work_factor_working
# metabolism_work_factor_idle
# metabolism_C
# metabolism_height_factor
# metabolism_mass_factor
# metabolism_B
# metabolism_age_factor
# metabolism_A
# fatal_co2_upper
# fatal_o2_lower
# medical_water_usage
# hygiene_water_usage
# consumed_water_usage
# max_energy
# max_arrival_age
# min_arrival_age


class HumanAgent(EnclosedAgent):

    _agent_type_name = "human"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # TODO populate std values with non-zero values in database
        mass_mean = self.get_agent_type_attribute("initial_mass_mean")
        mass_std = self.get_agent_type_attribute("initial_mass_std")
        age_mean = self.get_agent_type_attribute("initial_age_mean")
        age_std = self.get_agent_type_attribute("initial_age_std")
        height_mean = self.get_agent_type_attribute("initial_height_mean")
        height_std = self.get_agent_type_attribute("initial_height_std")

        initial_mass = self.model.random_state.normal(mass_mean, mass_std)
        initial_age = self.model.random_state.normal(age_mean, age_std)
        initial_height = self.model.random_state.normal(height_mean, height_std)

        self._attr("energy", self.get_agent_type_attribute("max_energy"), 
            is_client_attr=True, is_persisted_attr=True)

        self._attr("mass", initial_mass,is_client_attr=True, is_persisted_attr=True)
        self._attr("age", initial_age, is_client_attr=True, is_persisted_attr=True)
        self._attr("height", initial_height, is_client_attr=True, is_persisted_attr=True)

    def step(self):
        if self.structure is None:
            raise AgentModelError("Enclosing structure was not set for human agent.")

        timedelta_per_step = self.model.timedelta_per_step()
        hour_of_day = timedelta_hour_of_day(self.model.model_time)
        days_per_step = timedelta_to_days(timedelta_per_step)
        atmosphere = self.structure.atmosphere
        plumbing_system = self.structure.plumbing_system

        if(atmosphere is None
            or atmosphere.oxygen < self.get_agent_type_attribute("fatal_o2_lower")
            or atmosphere.carbon_dioxide > self.get_agent_type_attribute("fatal_co2_upper")):

            self.destroy()
        else:
            is_working = hour_of_day < self.get_agent_type_attribute("work_day_hours")
            self._metabolize(is_working, days_per_step)

            #atmosphere

            plumbing_system.water_to_waste(self._total_water_usage_per_day() * days_per_step)



    def _metabolize(self, is_working, days_per_step):
        # metabolism function from BVAD
        # (A - (age_factor*age(years)) + B(mass_factor*mass(kg) + height_factor*height(m)))/(C * work_factor * time(days))

        if is_working:
            work_factor = self.get_agent_type_attribute("metabolism_work_factor_working")
        else:
            work_factor = self.get_agent_type_attribute("metabolism_work_factor_idle")
            

        A = self.get_agent_type_attribute("metabolism_A")
        B = self.get_agent_type_attribute("metabolism_A")
        C = self.get_agent_type_attribute("metabolism_C")
        age_factor = self.get_agent_type_attribute("metabolism_age_factor")
        mass_factor = self.get_agent_type_attribute("metabolism_mass_factor")
        height_factor = self.get_agent_type_attribute("metabolism_height_factor")

        self.energy -= (A - (age_factor * self.age) + (B * (mass_factor * self.mass) + 
            (height_factor * self.height)))/(C * work_factor * days_per_step)
           
    def _total_water_usage_per_day(self):
        try:
            # try cached value
            return self._cached_total_water_usage_per_day
        except AttributeError as ex:
            consumed = self.get_agent_type_attribute("consumed_water_usage")
            hygiene = self.get_agent_type_attribute("hygiene_water_usage")
            medical = self.get_agent_type_attribute("medical_water_usage")

            self._cached_total_water_usage_per_day = consumed + hygiene + medical
            return self._cached_total_water_usage_per_day