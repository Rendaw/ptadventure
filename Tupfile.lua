tup.definerule
{
	inputs={'cairo/generate.py'},
	outputs=
	{
		'icon_col.png', 'icon_col-light.png',
		'icon_exc.png', 'icon_exc-light.png',
		'icon_inc.png', 'icon_inc-light.png',
		'icon_sort_asc.png', 'icon_sort_asc-light.png',
		'icon_sort_desc.png', 'icon_sort_desc-light.png',
		'icon_sort_rand.png', 'icon_sort_rand-light.png',
		'logo.png',
	},
	command='source env/bin/activate && python ./cairo/generate.py',
}

