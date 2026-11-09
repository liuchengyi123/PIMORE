import type { Product } from '@/api/products'
import flash1 from '@/assets/home/flash-1.jpg'
import flash2 from '@/assets/home/flash-2.jpg'
import flash3 from '@/assets/home/flash-3.jpg'
import flash4 from '@/assets/home/flash-4.jpg'
import neu1 from '@/assets/home/new-1.jpg'
import neu2 from '@/assets/home/new-2.jpg'
import neu3 from '@/assets/home/new-3.jpg'
import neu4 from '@/assets/home/new-4.jpg'
import just1 from '@/assets/home/just-1.jpg'
import just2 from '@/assets/home/just-2.jpg'

/** Local catalog used when the shop feed is unreachable. Live rows always win. */
export const shelf: Product[] = [
  {
    id: 'glass-food-storage', sku: 'glass-food-storage', name: '玻璃保鲜盒三件套',
    price: 6.29, compareAt: 14.99, category: '厨房', image: flash1,
    images: [flash1, flash2, flash4], blurb: '可叠放 · 密封', material: '高硼硅玻璃',
    sizes: ['三件套', '两件套'], onlyLeft: 36, tag: 'Deal',
  },
  {
    id: 'dish-drying-rack', sku: 'dish-drying-rack', name: '可折叠沥水架',
    price: 7.99, compareAt: 12.99, category: '厨房', image: flash2,
    images: [flash2, flash1], blurb: '可折叠 · 沥水', material: '不锈钢',
    sizes: ['标准'], tag: 'Deal',
  },
  {
    id: 'spray-bottles', sku: 'spray-bottles', name: '喷瓶两件套',
    price: 3.99, compareAt: 6.99, category: '清洁', image: flash3,
    images: [flash3, flash4], blurb: '细雾 · 厨房浴室', material: 'PET',
    onlyLeft: 42, tag: 'Flash',
  },
  {
    id: 'microfiber-cloths', sku: 'microfiber-cloths', name: '超细纤维抹布五条',
    price: 4.99, compareAt: 9.99, category: '清洁', image: flash4,
    images: [flash4, just2], blurb: '五条装', material: '超细纤维',
    sizes: ['五条'], tag: 'Deal',
  },
  {
    id: 'rolling-cart', sku: 'rolling-cart', name: '三层收纳车',
    price: 8.99, category: '收纳', image: neu1, images: [neu1, neu3],
    blurb: '带轮 · 三层', material: '塑料', tag: 'New',
  },
  {
    id: 'throw-blanket', sku: 'throw-blanket', name: '轻柔盖毯',
    price: 5.99, compareAt: 10.99, category: '家纺', image: neu2,
    images: [neu2, just2], blurb: '柔软 · 沙发盖毯', material: '涤纶',
    onlyLeft: 28, tag: 'New',
  },
  {
    id: 'storage-bins', sku: 'storage-bins', name: '可叠收纳盒三件',
    price: 7.49, category: '收纳', image: neu3, images: [neu3, neu1],
    blurb: '可叠放', material: 'PP', tag: 'New',
  },
  {
    id: 'utensil-set', sku: 'utensil-set', name: '硅胶厨具五件套',
    price: 4.99, category: '厨房', image: neu4, images: [neu4, flash1],
    blurb: '五件 · 耐热', material: '食品级硅胶', tag: 'New',
  },
  {
    id: 'desk-organizer', sku: 'desk-organizer', name: '桌面收纳',
    price: 6.49, category: '办公', image: just1, images: [just1, neu3],
    blurb: '分格收纳', material: '塑料', tag: 'New',
  },
  {
    id: 'bath-towels', sku: 'bath-towels', name: '速干浴巾',
    price: 8.99, compareAt: 16.99, category: '家纺', image: just2,
    images: [just2, neu2, flash4], blurb: '速干 · 柔软', material: '超细纤维',
    offers: [
      { id: 'coral', label: '珊瑚', price: 8.99, compareAt: 16.99 },
      { id: 'black', label: '黑色', price: 8.99, compareAt: 16.99 },
      { id: 'navy', label: '海军蓝', price: 8.99, compareAt: 16.99 },
      { id: 'olive', label: '橄榄绿', price: 8.99, compareAt: 16.99 },
      { id: 'gray', label: '灰色', price: 8.99, compareAt: 16.99 },
    ],
    tag: 'Deal',
  },
]

const bySku = new Map(shelf.map((p) => [p.sku, p]))

export function shelfProduct(sku: string): Product | undefined {
  return bySku.get(sku)
}

export function shelfFallback(live: Product[], take = 8): Product[] {
  return live.length ? live : shelf.slice(0, take)
}
