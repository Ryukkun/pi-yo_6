from discord import Embed, Colour


class EmBase:
    @classmethod
    def no_perm(self):
        '''
        権限がない時のEmbed
        '''
        return Embed(title=f'権限がありません 🥲', colour=Colour.red())
    
    @classmethod
    def failed(self):
        '''
        失敗した時のEmbed
        '''
        return Embed(title=f'失敗 🤯', colour=Colour.red())
    
    @classmethod
    def main_color(self):
        '''
        bot ベースカラー
        '''
        return Colour.light_grey()