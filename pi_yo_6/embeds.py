from discord import Embed, Colour


class EmBase:
    @staticmethod
    def no_perm():
        '''
        権限がない時のEmbed
        '''
        return Embed(title=f'権限がありません 🥲', colour=Colour.red())
    
    @staticmethod
    def failed():
        '''
        失敗した時のEmbed
        '''
        return Embed(title=f'失敗 🤯', colour=Colour.red())
    
    @staticmethod
    def main_color():
        '''
        bot ベースカラー
        '''
        return Colour.light_grey()