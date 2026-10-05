/** 공지 하나를 여는 주소. App 이 ?notice= 를 읽어 그 공지를 연다. */
export function noticeHref(id: number): string {
  return `/?notice=${id}`;
}
